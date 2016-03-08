$bootstrap = <<SCRIPT

# fix little things
locale-gen en_US.UTF-8 fr_FR.UTF-8 it_IT.UTF-8
apt-get update
apt-get -y install htop ntpdate

# iperf and iostat
apt-get -y install iperf sysstat

# python3 with pyvenv
apt-get -y install python3-venv python3-dev

# deps of python deps
apt-get -y install gfortran libopenblas-dev liblapack-dev

# OVS
apt-get -y install openvswitch-switch

# Docker
apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
echo deb https://apt.dockerproject.org/repo ubuntu-wily main > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get -y install linux-image-extra-$(uname -r)
apt-get -y install docker-engine
adduser vagrant docker

echo 'sudo bash --rcfile /vagrant/.vagrantrc ; exit' >> /home/vagrant/.bash_profile

>&2 echo "Provisioned! Now you REALLY SHOULD run vagrant reload in order to apply kernel changes!"
SCRIPT

Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/wily64"
  config.vm.hostname = "playground-dev"
  config.vm.provider "virtualbox" do |vb|
    vb.linked_clone = true if Vagrant::VERSION =~ /^1.8/
    vb.memory = 1536
    vb.cpus = 2
  end
  config.vm.provision :shell, inline: $bootstrap
  config.vm.provision :shell, inline: "ntpdate pool.ntp.org", run: "always"
end
