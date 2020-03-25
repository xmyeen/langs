#!/env/Python

import os,sys,tempfile,subprocess,shutil
from enum import Enum,unique
from dataclasses import dataclass

@unique
class Ver(Enum):
    centos = "7"
	cmake = "3.17.0"
    node = "10.1.0"
    python = "3.8.2"
    java = "11"
    fvs = "1.0.0"


LOCAL_MIRROR_ADDR_DEF = None

NAME = "langs"
MAINTAINER = "xmyeen@sina.com.cn"
IMG_FROM = f"centos:centos{Ver.centos.value}"

CMAKE_VERSION_DEF = f"{Ver.cmake.value}"
CMAKE_ARCHIVE_NAME_DEF = f"cmake-{CMAKE_VERSION_DEF}-Linux-x86_64"
CMAKE_GZ_ARCHIVE_DEF = f"{CMAKE_ARCHIVE_NAME_DEF}.tar.gz"
CMAKE_ARCHIVE_URL_DEF = f"{ LOCAL_MIRROR_ADDR_DEF or "https://github.com"}/Kitware/CMake/releases/download/v{CMAKE_ARCHIVE_NAME_DEF}/{CMAKE_GZ_ARCHIVE_DEF}"
CMAKE_HOME = f"/opt/{Ver.cmake.name}/"
CMAKE_PREFIX_ROOT_DEF = f"{CMAKE_HOME}{CMAKE_VERSION_DEF}/"

PYTHON_VERSION_DEF = f"{Ver.python.value}"
PYTHON_ARCHIVE_NAME_DEF = f"Python-{PYTHON_VERSION_DEF}"
PYTHON_XZ_ARCHIVE_DEF = f'{PYTHON_ARCHIVE_NAME_DEF}.tar.xz'
PYTHON_TAR_ARCHIVE_DEF,_ = os.path.splitext(PYTHON_XZ_ARCHIVE_DEF)
PYTHON_ARCHIVE_URL_DEF = f"{LOCAL_MIRROR_ADDR_DEF or 'https://www.python.org'}/ftp/python/{PYTHON_VERSION_DEF}/{PYTHON_XZ_ARCHIVE_DEF}"
PYTHON_HOME = f"/opt/{Ver.python.name}/"
PYTHON_PREFIX_ROOT_DEF = f"{PYTHON_HOME}{PYTHON_VERSION_DEF}/"

JAVA_YUM_PACKAGE_NAME_DEF = f"java-{Ver.java.value}-openjdk"
JAVA_HOME = f"/usr/lib/jvm/{JAVA_YUM_PACKAGE_NAME_DEF}/"

NODE_VERSION_DEF = f"{Ver.node.value}"
NODE_ARCHIVE_NAME_DEF = f"node-v{NODE_VERSION_DEF}-linux-x64"
NODE_XZ_ARCHIVE_DEF = f"{NODE_ARCHIVE_NAME_DEF}.tar.xz"
NODE_TAR_ARCHIVE_DEF,_ = os.path.splitext(NODE_XZ_ARCHIVE_DEF)
NODE_ARCHIVE_URL_DEF = f"{LOCAL_MIRROR_ADDR_DEF or 'https://nodejs.org'}/dist/v{NODE_VERSION_DEF}/{NODE_XZ_ARCHIVE_DEF}"
NODE_HOME = f"/opt/{Ver.node.name}/"
NODE_PREFIX_ROOT_DEF = f"{NODE_HOME}{NODE_VERSION_DEF}/"

FVS_VERSION_DFE = f"{Ver.fvs.value}"
FVS_ARCHIVE_NAME_DEF = f"fvs-{FVS_VERSION_DFE}-1"
FVS_RPM_ARCHIVE_DEF = f"{FVS_ARCHIVE_NAME_DEF}.el7.noarch.rpm"
FVS_ARCHIVE_URL_DEF = f"{LOCAL_MIRROR_ADDR_DEF or 'https://github.com'}/xmyeen/fvs/releases/download/{FVS_VERSION_DFE}-beta/{FVS_RPM_ARCHIVE_DEF}"

RUSTUP_REGISTRY = "mirrors.sjtug.sjtu.edu.cn"

ENTRYPOINT_SCRIPT_PATH = "/usr/bin/forever"

image_building_script_content_str = f'''
#!/bin/sh

BASH_PROFILE="${{HOME}}/.bashrc"
BUILD_ROOT="/tmp/{NAME}-build-directory/"
ARCHIVES_ROOT="${{BUILD_ROOT}}archives/"

#0. 生成目录
mkdir -p ${{ARCHIVES_ROOT}} 
cd ${{BUILD_ROOT}}

#1. 阿里云YUM镜像
#/bin/sh
rm -rf /etc/yum.repos.d/* && 
curl -k -s -o  /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-{Ver.centos.value.split(".")[0]}.repo && 
yum makecache

#2. 设置中文环境
echo "export LC_ALL=zh_CN.UTF-8"  >> /etc/locale.conf && 
yum install -y kde-l10n-Chinese && 
yum -y reinstall glibc-common && 
localedef -c -f UTF-8 -i zh_CN zh_CN.utf8
cat >> ${{BASH_PROFILE}} <<EOF

# languages
export LANG=zh_CN.UTF-8
export LANGUAGE=zh_CN:zh
export LC_ALL=zh_CN.UTF-8
EOF
source ${{BASH_PROFILE}}

#3. 安装基础软件
yum install -y vim unzip bzip2 git svn rpm-build

#4. 安装c++开发环境
yum install -y gcc gcc-c++ make glibc
mkdir -p {CMAKE_HOME}
curl -skL -o ${{ARCHIVES_ROOT}}{CMAKE_GZ_ARCHIVE_DEF} {CMAKE_ARCHIVE_URL_DEF} &&
tar zxvf ${{ARCHIVES_ROOT}}{CMAKE_GZ_ARCHIVE_DEF} -C {CMAKE_HOME}
mv {CMAKE_HOME}{CMAKE_ARCHIVE_NAME_DEF} {os.path.dirname(CMAKE_PREFIX_ROOT_DEF)}
cat >> ${{BASH_PROFILE}} <<EOF

# cmake
export LD_LIBRARY_PATH={CMAKE_PREFIX_ROOT_DEF}lib:\\${{LD_LIBRARY_PATH}}
export PATH=\\${{PATH}}:{CMAKE_PREFIX_ROOT_DEF}bin
EOF

#5. 安装python开发环境
yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel libffi-devel
curl -skL -o ${{ARCHIVES_ROOT}}{PYTHON_XZ_ARCHIVE_DEF} {PYTHON_ARCHIVE_URL_DEF}
xz -d ${{ARCHIVES_ROOT}}{PYTHON_XZ_ARCHIVE_DEF}
tar xvf ${{ARCHIVES_ROOT}}{PYTHON_TAR_ARCHIVE_DEF} -C ${{BUILD_ROOT}} 
cd ${{BUILD_ROOT}}{PYTHON_ARCHIVE_NAME_DEF}
./configure --prefix={PYTHON_PREFIX_ROOT_DEF} --enable-shared --with-libs='/usr/lib64/libcrypto.so /usr/lib64/libssl.so' --with-ssl
make
make install
cat > /etc/pip.conf <<EOF
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/ 
trusted-host = mirrors.aliyun.com
disable-pip-version-check = false
timeout = 120
EOF

cat >> ${{BASH_PROFILE}} <<EOF

# Python
export LD_LIBRARY_PATH={PYTHON_PREFIX_ROOT_DEF}lib:${{LD_LIBRARY_PATH}}
export PATH=\\${{PATH}}:{PYTHON_PREFIX_ROOT_DEF}bin
EOF
cd - > /dev/null

sh -i -l <<EOF
source ${{BASH_PROFILE}}
python3 -m pip install wheel
EOF

#5. 安装java开发环境
yum install -y {JAVA_YUM_PACKAGE_NAME_DEF} {JAVA_YUM_PACKAGE_NAME_DEF}-devel maven
cat >> ${{BASH_PROFILE}} <<EOF

# Java
export JAVA_HOME={os.path.dirname(JAVA_HOME)}
export CLASSPATH=.:\\${{JAVA_HOME}}/lib:\\${{JAVA_HOME}}/lib/dt.jar:\\${{JAVA_HOME}}/lib/tools.jar
export PATH=\\${{PATH}}:\\${{JAVA_HOME}}/bin
EOF
# MAVEN的SETTINGS设置

#6. 安装nodejs开发环境
mkdir -p {NODE_HOME}
curl -skL -o ${{ARCHIVES_ROOT}}{NODE_XZ_ARCHIVE_DEF} {NODE_ARCHIVE_URL_DEF}
xz -d ${{ARCHIVES_ROOT}}{NODE_XZ_ARCHIVE_DEF}
tar xvf ${{ARCHIVES_ROOT}}{NODE_TAR_ARCHIVE_DEF} -C {NODE_HOME}
mv {NODE_HOME}{NODE_ARCHIVE_NAME_DEF} {os.path.dirname(NODE_PREFIX_ROOT_DEF)}
cat >> ${{BASH_PROFILE}} <<EOF

# Node
export LD_LIBRARY_PATH={NODE_PREFIX_ROOT_DEF}lib:\\${{LD_LIBRARY_PATH}}
export PATH=\\${{PATH}}:{NODE_PREFIX_ROOT_DEF}bin
EOF

#7. 安装rust开发环境
export RUSTUP_DIST_SERVER=https://{RUSTUP_REGISTRY}/rust-static
export RUSTUP_UPDATE_ROOT=${{RUSTUP_DIST_SERVER}}/rustup

curl https://sh.rustup.rs -sSf | sh -s -- -y

cat >> ${{BASH_PROFILE}} <<EOF

# 安装Rust环境
export RUSTUP_DIST_SERVER=${{RUSTUP_DIST_SERVER}}
export RUSTUP_UPDATE_ROOT=${{RUSTUP_UPDATE_ROOT}}
EOF

cat >> ${{HOME}}/.cargo/config <<EOF
[source.crates-io]
registry = "https://github.com/rust-lang/crates.io-index"
replace-with = 'ustc'

[source.ustc]
registry = 'git://{{RUSTUP_REGISTRY}}/crates.io-index
EOF

#7. 安装go开发环境
GO_WORKSPACE=${{HOME}}/gowork
yum install -y golang
mkdir -p ${{GO_WORKSPACE}}
cat >> ${{BASH_PROFILE}} <<EOF

# Go
export GOPATH=${{GO_WORKSPACE}}
export PATH=\\${{PATH}}:\\${{GOPATH}}/bin
EOF

#8. 安装文件服务器
curl -skL -O {FVS_ARCHIVE_URL_DEF} &&
rpm -ivh {FVS_RPM_ARCHIVE_DEF} &&
rm -f {FVS_RPM_ARCHIVE_DEF}

#9. 构建ssh环境
yum install -y openssh openssh-server openssh-client
mkdir -p /var/run/sshd
echo "root:abc123" | chpasswd
ssh-keygen -q -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N ''
ssh-keygen -q -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -N ''
ssh-keygen -t dsa -f /etc/ssh/ssh_host_ed25519_key  -N ''
# sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
sed -i /etc/ssh/sshd_config \\
    -e 's/#UsePrivilegeSeparation.*/UsePrivilegeSeparation no/g' \\
    -e 's/UsePAM.*/UsePAM no/g' \\
    -e 's/#UsePAM no/UsePAM no/g' \\
    -e 's~^PasswordAuthentication yes~PasswordAuthentication yes~g' \\
    -e 's~^#PermitRootLogin yes~PermitRootLogin yes~g' \\
    -e 's~^#UseDNS yes~UseDNS no~g' \\
    -e 's~^\\(.*\\)/usr/libexec/openssh/sftp-server$~\\1internal-sftp~g'

#9. 生成启动脚本(改为使用systemd服务，让容器更像虚拟机，所以无需单独的启动脚本了)
cat >> {ENTRYPOINT_SCRIPT_PATH} <<EOF
#!/bin/sh
cat /etc/motd
/bin/sh -c "exec /usr/sbin/init"

/usr/sbin/sshd -D
EOF
chmod +x {ENTRYPOINT_SCRIPT_PATH}

#10. 安装证书
# 安装证书
# echo -n | \
# openssl s_client -showcerts -connect hub.docker.com:443 2>/dev/null | \
# sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >> /etc/ssl/certs/ca-certificates.crt
# openssl s_client -showcerts -connect hub.docker.com:443 2>/dev/null | \
# sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /etc/ssl/certs/docker-hub-certificates.crt
# update-ca-trust

#11. 清理
rm -rf ${{BUILD_ROOT}}
yum clean all

#结束
echo "Finish all"
'''

image_dockerfile_content_str = f'''
FROM {IMG_FROM}

MAINTAINER {MAINTAINER}

ENV LANG="zh_CN.UTF-8" LC_ALL="zh_CN.UTF-8" LANGUAGE="zh_CN:zh"

ARG builder_sh
ADD ${{builder_sh}} /tmp/

RUN \\
	# 将编译时间加入登录提示
	echo "Built in `date "+%Y%m%dT%H%M%S%z"`" >> /etc/motd; \\
	# 将环境变量写到/etc/profile里面，保证SSH登录的时候能够正确使用
	# 执行编译脚本
	sh /tmp/${{builder_sh}}; \\
	# 删除编译脚本
	rm -f /tmp/${{build_sh}}; \\
	# 设置{os.path.basename(ENTRYPOINT_SCRIPT_PATH)}脚本可用
	# chmod 755 {ENTRYPOINT_SCRIPT_PATH}
	(cd /lib/systemd/system/sysinit.target.wants/; \\
	for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \\
	rm -f /lib/systemd/system/multi-user.target.wants/*; \\
	rm -f /etc/systemd/system/*.wants/*; \\
	rm -f /lib/systemd/system/local-fs.target.wants/*; \\
	rm -f /lib/systemd/system/sockets.target.wants/*udev*; \\
	rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \\
	rm -f /lib/systemd/system/basic.target.wants/*; \\
	rm -f /lib/systemd/system/anaconda.target.wants/*;

EXPOSE 22 8080 34433

VOLUME [ "/sys/fs/cgroup" ]

CMD ["{ENTRYPOINT_SCRIPT_PATH}"]
# CMD ["/usr/sbin/sshd -D"]
# CMD ["/usr/sbin/init"]
'''

tmpdir = tempfile.mkdtemp()

try:
	with tempfile.NamedTemporaryFile(mode='w+', dir=tmpdir) as dockerfile_f:
		dockerfile_f.write(image_dockerfile_content_str)
		dockerfile_f.flush()

		sh_f = tempfile.NamedTemporaryFile(mode='w+', dir=tmpdir)
		sh_f.write(image_building_script_content_str)
		sh_f.flush()


		cmdline = ' '.join([
			'docker',
			'build',
			'--force-rm',
			# '--pull',
			'--no-cache',
			'--build-arg HTTP_PROXY=${HTTP_PROXY}',
			'--build-arg HTTPS_PROXY=${HTTPS_PROXY}',
			f'--build-arg builder_sh={os.path.basename(sh_f.name)}',
			f'-t {NAME}:latest',
			f'-f {dockerfile_f.name}',
			tmpdir
		])
		print(f'Command: {cmdline}')
		
		# if subprocess.call(f'docker build {" ".join(cmdline_opts)} .', shell=True):
		# 	print("Build image failed")
		if subprocess.call(cmdline, shell=True, cwd=tmpdir):
			print("Build image failed")

		sh_f.seek(0)
		sh_f.close()
		dockerfile_f.seek(0)
except:
	pass

shutil.rmtree(tmpdir, ignore_errors=True)
# os.removedirs(tmpdir)