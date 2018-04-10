Vagrant.configure("2") do |config|
    config.vm.box = "bento/centos-7.2"
    config.vm.synced_folder ".", "/home/vagrant/yurika"
    config.vm.network "forwarded_port", guest: 8000, host: 8080
    config.vm.network "forwarded_port", guest: 6379, host: 6379  # redis-server
    config.vm.network "forwarded_port", guest: 9200, host: 9200  # elasticsearch
end
