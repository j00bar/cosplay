Cosplay
=======

Cosplay is an experimental project for building RPMs from containers, complete
with configuration, persistent storage, and systemd unit files.

Red Hat has the concept of [system containers][1] for running system daemons
as containers, however the installation and distribution of these containers
is done using container tools. For people who wish to distribute an RPM and
manage content streams using RPM-based tools, this is inadequate.

Cosplay aims to offer this alternative.

[1]: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux_atomic_host/7/html/managing_containers/running_system_containers
