import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile

import dateutil.parser
import jinja2

logger = logging.getLogger(__name__)

install_dir = os.path.dirname(__file__) or os.getcwd()


def get_context_for_image(temp_dir, image, base, service, ports, env, vol):
    result = subprocess.run(f'/usr/bin/podman inspect {image}'.split(' '),
                            capture_output=True)
    if result.returncode != 0:
        raise ValueError(f'Podman could not inspect the specified image: '
                         f'{result.stderr}')
    image_data = json.loads(result.stdout)
    created_dt = dateutil.parser.parse(image_data[0]['Created'])

    if base != 'scratch':
        result = subprocess.run(f'/usr/bin/podman inspect {base}'.split(' '),
                                capture_output=True)
        if result.returncode != 0:
            raise ValueError(f'Podman could not inspect the base image: '
                             f'{result.stderr}')
        base_image_data = json.loads(result.stdout)
        base_created_dt = dateutil.parser.parse(base_image_data[0]['Created'])
        base_full_package, base_version = base.rsplit(':', 1)
        base_package = base_full_package.rsplit('/', 1)[-1]

    package, version = image.rsplit(':', 1)
    package_host, package_name = package.rsplit('/', 1)
    context = dict(
        temp_dir=temp_dir,
        package=package_name,
        package_host=package_host,
        version=version,
        version_datestring=created_dt.strftime('%Y%m%d%H%M%S'),
        summary=f'RPM package for container image {image}',
        cosplay_dir=install_dir,
        service=service
    )
    if service:
        context['network_args'] = ' '.join(f'-p {p}' for p in ports) if ports else ''
        context['environment_args'] = ' '.join(f'-e {e}' for e in env) if env else ''
        context['volume_args'] = ' '.join(f'-v {v}' for v in vol) if vol else ''
    if base != 'scratch':
        context.update(dict(
            base=base_package,
            base_version=base_version,
            base_version_datestring=base_created_dt.strftime('%Y%m%d%H%M%S'),
        ))
    return context


def main(image, base, service, ports, env, vol):
    temp_dir = tempfile.mkdtemp()
    try:
        context = get_context_for_image(temp_dir, image, base, service, ports, env, vol)
        logger.debug(f'Context: {context}')

        spec_template_file = ('baseos' if base == 'scratch' else 'package') + '.spec'
        with open(os.path.join(install_dir, spec_template_file + '.j2')) as ifs:
            spec_template = jinja2.Template(ifs.read())
        with open(os.path.join(temp_dir, spec_template_file), 'w') as ofs:
            ofs.write(spec_template.render(context))

        if service:
            with open(os.path.join(install_dir, 'package.service.j2')) as ifs:
                service_template = jinja2.Template(ifs.read())
            with open(os.path.join(temp_dir, context['package'] + '.service'), 'w') as ofs:
                ofs.write(service_template.render(context))

        result = subprocess.run(f'/usr/bin/rpmbuild -bb {spec_template_file}'.split(' '),
                                cwd=temp_dir)
        if result.returncode != 0:
            raise RuntimeError(f'Could not build package: {result.stderr}')
        logger.info('Build complete.')
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            logger.warning(f'Could not remove temporary directory {temp_dir}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Cosplay is a tool to wrap a container image in an RPM.')
    parser.add_argument('--base', required=True,
                        help='The OS base container image to require')
    parser.add_argument('--no-service', action='store_false', dest='service',
                        help='Do not build a systemd unit file for this service')
    parser.add_argument('--ports', type=lambda s: s.split(','),
                        help='Comma-separated list of network ports to open '
                             'for this service')
    parser.add_argument('--env', '-e', nargs='*',
                        help='Runtime environment variables, in var=value '
                             'notation')
    parser.add_argument('--vol', nargs='*',
                        help='Volumes to export into the container, in '
                             'local-dir:target-mountpoint notation')
    parser.add_argument('image', help='The container image to wrap')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    try:
        main(**vars(args))
    except Exception as e:
        logger.exception(f'Error: {e}')
        sys.exit(1)
