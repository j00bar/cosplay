#!/usr/bin/env python3

import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


def main(skopeo_dir, base_image):
    if not os.path.exists(skopeo_dir):
        logger.error(f'Skopeo dir output not found at {skopeo_dir}')
        sys.exit(1)
    with open(os.path.join(skopeo_dir, 'manifest.json')) as ifs:
        manifest = json.load(ifs)
    proc_out = subprocess.run(
        f'/usr/bin/podman inspect {base_image}'.split(' '),
        capture_output=True)
    base_image_data = json.loads(proc_out.stdout)
    base_image_layers = base_image_data[0]['RootFS']['Layers']
    manifest_layers = manifest['layers']
    pruned_layers = [layer for layer in manifest_layers
                     if layer['digest'] not in base_image_layers]
    manifest['layers'] = pruned_layers
    with open(os.path.join(skopeo_dir, 'manifest.json'), 'w') as ofs:
        json.dump(manifest, ofs)
    for layer in base_image_layers:
        layer_hash = layer.split(':', 1)[-1]
        layer_path = os.path.join(skopeo_dir, layer_hash)
        if os.path.exists(layer_path):
            logger.info(f'Removing layer {layer_hash}')
            os.remove(layer_path)
    dir_size = sum(os.path.getsize(f) 
                   for f in os.listdir(skopeo_dir) if os.path.isfile(f))
    logger.info(f'Pruning complete. Final manifest size: {dir_size}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        skopeo_dir, base_image = sys.argv[1:]
    except ValueError:
        logger.error(f'Usage: {sys.argv[0]} skopeo_dir '
                     f'base_image:base_version')
    main(skopeo_dir, base_image)
