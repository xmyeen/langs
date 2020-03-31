#!/env/Python

import os,sys,tempfile,subprocess,shutil,configparser,warnings
from urllib import parse
from enum import Enum,unique
from collections import namedtuple
from dataclasses import dataclass

ENTRYPOINT_SCRIPT_PATH = "/usr/sbin/forever"

@unique
class CompressionDefs(Enum):
    XZ = ".tar.xz"
    GZ = ".tar.gz"
    BZ = ".tar.bz"
    BZ2 = ".tar.bz2"
    Z = ".tar.Z"
    ZIP = ".zip"
    RPM = ".rpm"

@unique
class GroupDefs(Enum):
    ssh = 1
    common = 2
    cpp = 101
    python = 102
    js = 103
    java = 104
    golang = 105
    rust = 106
    tool = 9

@unique
class InstallDefs(Enum):
    yum = 1
    http = 2
    filesystem = 3
    rpm = 4
    custom = 5

@unique
class OperateSystemDef(Enum):
    centos = "7"

PKG_INFO_STR = f'''
[openssh]
group = {GroupDefs.ssh.name}
install = {InstallDefs.yum.name}

[openssh-server]
group = {GroupDefs.ssh.name}
install = {InstallDefs.yum.name}

[openssh-client]
group = {GroupDefs.ssh.name}
install = {InstallDefs.yum.name}

[vim]
group = {GroupDefs.common.name}
install = {InstallDefs.yum.name}

[unzip]
group = {GroupDefs.common.name}
install = {InstallDefs.yum.name}

[bzip2]
group = {GroupDefs.common.name}
install = {InstallDefs.yum.name}
url = {{name}} {{name}}-devel

[git]
group = {GroupDefs.common.name}
install = {InstallDefs.yum.name}

[svn]
group = {GroupDefs.common.name}
install = {InstallDefs.yum.name}

[rpm-build]
group = {GroupDefs.common.name}
install = {InstallDefs.yum.name}

[gcc]
group = {GroupDefs.cpp.name}
install = {InstallDefs.yum.name}

[gcc-c++]
group = {GroupDefs.cpp.name}
install = {InstallDefs.yum.name}

[make]
group = {GroupDefs.cpp.name}
install = {InstallDefs.yum.name}

[glibc]
group = {GroupDefs.cpp.name}
install = {InstallDefs.yum.name}

[cmake]
group = {GroupDefs.cpp.name}
install = {InstallDefs.http.name}
version = 3.15.2
url = https://github.com/Kitware/CMake/releases/download/v{{version}}/cmake-{{version}}-Linux-x86_64{CompressionDefs.GZ.value}

[zlib]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[openssl]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[ncurses]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[sqlite]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[readline]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[tk]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[libffi]
group = {GroupDefs.python.name}
install = {InstallDefs.yum.name}
url = {{name}}-devel

[python]
group = {GroupDefs.python.name}
install = {InstallDefs.http.name}
version = 3.8.2
url = https://www.python.org/ftp/python/{{version}}/Python-{{version}}{CompressionDefs.XZ.value}

[node]
group = {GroupDefs.js.name}
install = {InstallDefs.http.name}
version = 10.1.0
url = https://nodejs.org/dist/v{{version}}/node-v{{version}}-linux-x64{CompressionDefs.XZ.value}

[openjdk]
group = {GroupDefs.java.name}
install = {InstallDefs.yum.name}
version = 11
url = java-{{version}}-{{name}} java-{{version}}-{{name}}-devel

[maven]
group = {GroupDefs.java.name}
install = {InstallDefs.yum.name}

[golang]
group = {GroupDefs.golang.name}
install = {InstallDefs.http.name}
version = 1.14
url = https://mirrors.ustc.edu.cn/golang/go{{version}}.linux-amd64{CompressionDefs.GZ.value}

[rust]
group = {GroupDefs.rust.name}
install = {InstallDefs.custom.name}
version = 

[fvs]
group = {GroupDefs.tool.name}
install = {InstallDefs.rpm.name}
version = 1.0.0
url = https://github.com/xmyeen/fvs/releases/download/{{version}}-beta.3/fvs-{{version}}-1.el7.noarch{CompressionDefs.RPM.value}
'''

@dataclass
class Pkg:
    name: str
    version : str
    install : str
    group : str
    url : str

class ShCoder(object):
    def __init__(self, internal_hub = None, *groups):
        self.__internal_hub = internal_hub
        self.__groups = groups
        self.__build_root = '/opt/langs-build'
        self.__cp = configparser.ConfigParser()

    @property
    def name(self):
        return "langs"

    @property
    def maintainer(self):
        return "xmyeen xmyeen@sina.com.cn"

    @property
    def internal_hub(self):
        return self.__internal_hub

    def get_internal_mirror(self, name):
        return f'{self.__internal_hub}/{name}'

    @property
    def archive_home(self):
        return f'{self.__build_root}/.archives'

    def get_home(self, pkg):
        if pkg.version:
            return f'/opt/{pkg.name}/{pkg.version}'
        else:
            return f'/opt/{pkg.name}'

    def get_url(self, pkg):
        u = pkg.url.format(name = pkg.name, version = pkg.version)
        parsed = parse.urlparse(u)
        if parsed.scheme and self.internal_hub:
            u = self.get_internal_mirror(pkg.name) + u[len(parsed.scheme) + 3 + len(parsed.netloc):]
        return u

    def load_configuration(self, cfg_str):
        '''读取配置信息
        '''
        self.__cp.read_string(cfg_str)

    def get_centos_image_info(self):
        return f"centos:centos{OperateSystemDef.centos.value}"

    def get_local_mirror_address(self, name):
        return self.__internal_hub + '/' + name

    def configure_yum_repos(self, *names):
        ''' 设置YUM镜像的代码片段
        '''
        lines = []
        
        lines.append("rm -rf /etc/yum.repos.d/*")

        # lines.extend([
        #     f'echo "--- Add usts repository"',
        #     f'curl -k -s -L -o /etc/yum.repos.d/CentOS-Base.repo https://lug.ustc.edu.cn/wiki/_export/code/mirrors/help/centos?codeblock=3'
        # ])

        name = 'aliyun'
        if not names or name.lower() in names:
            lines.extend([
                f'echo "--- Add {name} repository"',
                f'curl -k -s -L -o /etc/yum.repos.d/{name}.repo https://mirrors.aliyun.com/repo/Centos-{OperateSystemDef.centos.value}.repo',
                f"sed -i -e '/mirrors.cloud.aliyuncs.com/d' -e '/mirrors.aliyuncs.com/d' /etc/yum.repos.d/{name}.repo"
            ])

        name = 'netease'
        if not names or name.lower() in names:
            lines.extend([
                f'echo "--- Add {name} repository"',
                f'curl -k -s -L -o /etc/yum.repos.d/{name}.repo https://mirrors.163.com/.help/CentOS{OperateSystemDef.centos.value}-Base-163.repo'
            ])

        lines.append("yum makecache")

        return '\n'.join(lines)

    def install_softwares(self):
        lines = []

        gpkgs = {}

        for section in self.__cp.sections():
            d = dict(group = None, install = None, version = None, url = None)
            d.update(dict(list(self.__cp.items(section))))
            if 'group' not in d:
                continue
            if d.get('group') not in self.__groups:
                continue
            if d.get('group') not in gpkgs:
                gpkgs.update({ d.get('group') : [] })

            gpkgs.get(d.get('group')).append(Pkg(name = section, **d))

        for g in self.__groups:
            pkgs = gpkgs.get(g, None)
            if not pkgs:
                continue

            lines.append(f'#- Install {g} group')
            for p in pkgs:
                if InstallDefs.yum.name == p.install:
                    lines.append(self.__yum(p))
                elif InstallDefs.rpm.name == p.install:
                    lines.append(self.__rpm(p))

                f = getattr(self, f'install_{p.name.replace("-", "_")}', None)
                if f:
                    lines.append(f'#--- Install {p.name}')
                    lines.append(f(p))

            f = getattr(self, f'after_group_{g.replace("-", "_")}', None)
            if f: lines.append(f())
            lines.append(f'\n\n')

        return '\n'.join([l for l in lines if l])

    def __download(self, install, url, output_dir = None):
        lines = []
        filepath = f"{self.archive_home}/{os.path.basename(url)}"

        lines.append(f"cd {self.__build_root}")

        if InstallDefs.http.name == install:
            if url.startswith('file://'):
                lines.append(f'mv -f {url[7:]} {self.archive_home}')
            elif url.startswith('http'):
                lines.append(f"curl -skL -o {filepath} {url}")
        else:
            Warning.warn(f"Code downloading failed - install({install});url({url})")
            return

        if output_dir:
            lines.append(f'rm -rf {output_dir} &&')
            lines.append(f'mkdir -p {os.path.dirname(output_dir)} &&')
        lines.append('temp_dir=`mktemp -d ./tmpd.XXXXXX` &&')
        if filepath.endswith(CompressionDefs.XZ.value):
            lines.append(f"xz -d {filepath} &&")
            lines.append(f"tar -xvf {filepath[:-3]} -C ${{temp_dir}} &&")
        elif filepath.endswith(CompressionDefs.GZ.value):
            lines.append(f"tar -zxvf {filepath} -C ${{temp_dir}} &&")
        elif filepath.endswith(CompressionDefs.BZ).value:
            lines.append(f"tar -jxvf {filepath} -C ${{temp_dir}} &&")
        elif filepath.endswith(CompressionDefs.BZ2.value):
            lines.append(f"tar -jxvf {filepath} -C ${{temp_dir}} &&")
        elif filepath.endswith(CompressionDefs.Z):
            lines.append(f"tar -Zxvf {filepath} -C ${{temp_dir}} &&")
        elif filepath.endswith(CompressionDefs.TAR.value):
            lines.append(f"tar -xvf {filepath} -C ${{temp_dir}} &&")
        elif filepath.endswith(CompressionDefs.ZIP.value):
            lines.append(f"unzip {filepath} -d ${{temp_dir}} &&")
        # elif filepath.endswith(CompressionDefs.RPM.value):
        #     lines.append(f"cd {output_dir} && {{ rpm2cpio {filepath} | cpio -div }} && cd - >/dev/null")
        if output_dir:
            lines.append(f"find $temp_dir -maxdepth 1 -mindepth 1 -type d -execdir mv -vf {{}} {output_dir} \; &&")
            lines.append("rm -rf $temp_dir &&")
            lines.append("unset temp_dir &&")
            lines.append(f"output_dir={output_dir}")
        else:
            lines.append(f"output_dir=\"$(find $temp_dir -maxdepth 1 -mindepth 1 -type d)\"")

        lines.append(f"cd - >/dev/null")

        return "\n".join(lines)

    def __yum(self, *pkgs):
        lines = []

        if not pkgs:
            return ''

        rpms = []
        for p in pkgs:
            if p.url:
                rpms.append(self.get_url(p))
            elif p.version:
                rpms.append(f"{p.name}-{p.version}")
            else:
                rpms.append(p.name)

        rpm_str = " ".join(rpms)
        lines.append(f'#--- Install {rpm_str}')
        lines.append(f'yum install -y {rpm_str}')

        return '\n'.join(lines)

    def __rpm(self, *pkgs):
        lines = []

        if not pkgs:
            return

        for p in pkgs:
            lines.append(f'#--- Install {p.name}')
            lines.append(f'rpm -ivh {self.get_url(p)}')

        return '\n'.join(lines)

    def install_cmake(self, pkg):
        home_dir = self.get_home(pkg)

        content_str = f'''
        {self.__download(install = pkg.install, url = self.get_url(pkg), output_dir = home_dir)}
        cat >> ${{BASH_PROFILE}} <<EOF

        # cmake
        export LD_LIBRARY_PATH={home_dir}/lib:\\${{LD_LIBRARY_PATH}}
        export PATH=\\${{PATH}}:{home_dir}/bin
        EOF
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def install_python(self, pkg):
        home_dir = self.get_home(pkg)

        content_str = f'''
        mkdir -p {home_dir}
        {self.__download(install = pkg.install, url = self.get_url(pkg))}
        cd $output_dir
        ./configure --prefix={home_dir} --enable-shared --with-libs='/usr/lib64/libcrypto.so /usr/lib64/libssl.so' --with-ssl
        make
        make install
        cd {self.__build_root}
        rm -rf $output_dir

        cat > /etc/pip.conf <<EOF
        [global]
        timeout = 120
        index-url = https://mirrors.aliyun.com/pypi/simple/

        [install]
        trusted-host = mirrors.aliyun.com
        disable-pip-version-check = false
        EOF

        cat >> ${{BASH_PROFILE}} <<EOF

        # Python
        export LD_LIBRARY_PATH={home_dir}/lib:\\${{LD_LIBRARY_PATH}}
        export PATH=\\${{PATH}}:{home_dir}/bin
        EOF

        sh -i -l <<EOF
        source ${{BASH_PROFILE}}
        python3 -m pip install wheel pipenv
        EOF
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def install_node(self, pkg):
        home_dir = self.get_home(pkg)

        content_str = f'''
        mkdir -p {home_dir}
        {self.__download(install = pkg.install, url = self.get_url(pkg), output_dir = home_dir)}
        cat >> ${{BASH_PROFILE}} <<EOF

        # Node
        export LD_LIBRARY_PATH={home_dir}/lib:\\${{LD_LIBRARY_PATH}}
        export PATH=\\${{PATH}}:{home_dir}/bin
        EOF
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def install_openjdk(self, pkg):
        content_str = f'''
        cat >> ${{BASH_PROFILE}} <<EOF

        # Java
        export JAVA_HOME=/usr/lib/jvm/java-{pkg.version}-openjdk/
        export CLASSPATH=.:\\${{JAVA_HOME}}/lib:\\${{JAVA_HOME}}/lib/dt.jar:\\${{JAVA_HOME}}/lib/tools.jar
        export PATH=\\${{PATH}}:\\${{JAVA_HOME}}/bin
        EOF
        # MAVEN的SETTINGS设置
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def install_rust(self, pkg):
        RUSTUP_REGISTRY = "mirrors.sjtug.sjtu.edu.cn"
        RUSTUP_REGISTRY_NAME = "utsc"

        content_str = f'''
        ENV_FILE="$HOME/.rust-env"

        cat >> $ENV_FILE <<EOF
        # 安装Rust环境
        export RUSTUP_DIST_SERVER=https://{RUSTUP_REGISTRY}/rust-static
        export RUSTUP_UPDATE_ROOT=\\${{RUSTUP_DIST_SERVER}}/rustup
        EOF

        source $ENV_FILE
        curl https://sh.rustup.rs -sSf | sh -s -- -y

        cat $ENV_FILE >> ${{BASH_PROFILE}}

        cat >> $HOME/.cargo/config <<EOF
        [source.crates-io]
        registry = "https://github.com/rust-lang/crates.io-index"
        replace-with = '{RUSTUP_REGISTRY_NAME}'

        [source.{RUSTUP_REGISTRY_NAME}]
        registry = 'git://{RUSTUP_REGISTRY}/crates.io-index
        EOF

        rm -f ${{ENV_FILE}}
        unset ENV_FILE
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def install_golang(self, pkg):
        home_dir = self.get_home(pkg)

        content_str = f'''
        mkdir -p {home_dir}
        {self.__download(install = pkg.install, url = self.get_url(pkg), output_dir = home_dir)}

        GO_WORKSPACE=${{HOME}}/gowork
        mkdir -p ${{GO_WORKSPACE}}
        cat >> ${{BASH_PROFILE}} <<EOF

        # Go
        export GOPATH=${{GO_WORKSPACE}}
        export PATH=\\${{PATH}}:{home_dir}/bin
        EOF
        unset GO_WORKSPACE
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def after_group_ssh(self):
        content_str = f'''
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
        '''
        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])

        return content_str

    def after_group_common(self):
        return "git config --global http.sslVerify false"

    def after_group_cpp(self):
        return ''

    def after_group_python(self):
        return ''

    def after_group_node(self):
        return ''

    def after_group_java(self):
        return ''

    def after_group_rust(self):
        return ''

    def after_group_golang(self):
        return ''

    def get_software_script_content(self):
        content_str = f'''
        #!/bin/sh
        BASH_PROFILE="${{HOME}}/.bashrc"

        #生成目录
        mkdir -p {self.archive_home}
        cd {self.__build_root}

        #国内YUM镜像
        {self.configure_yum_repos()}

        #设置中文环境
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

        {self.install_softwares()}

        # entrypint
        cat >> {ENTRYPOINT_SCRIPT_PATH} <<EOF
        #!/bin/sh
        cat /etc/motd
        systemctl enable sshd.service
        exec /usr/sbin/init
        EOF
        chmod +x {ENTRYPOINT_SCRIPT_PATH}

        # 安装证书
        # echo -n | \\
        # openssl s_client -showcerts -connect hub.docker.com:443 2>/dev/null | \\
        # sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' >> /etc/ssl/certs/ca-certificates.crt
        # openssl s_client -showcerts -connect hub.docker.com:443 2>/dev/null | \\
        # sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /etc/ssl/certs/docker-hub-certificates.crt
        # update-ca-trust

        #清理
        rm -rf {self.__build_root}
        yum clean all

        #结束
        echo "Finish all"
        '''

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])
        return content_str

    def get_dockerfile_content(self):
        language_str = " ".join([ name for name, en in GroupDefs.__members__.items() if 100 <= en.value ])

        content_str = f'''
        FROM {self.get_centos_image_info()}

        MAINTAINER {self.maintainer}

        ENV LANG="zh_CN.UTF-8" LC_ALL="zh_CN.UTF-8" LANGUAGE="zh_CN:zh"

        LABEL description="集合多种开发语言环境" language="{language_str}"

        ARG builder_sh
        ADD ${{builder_sh}} /tmp/

        RUN \\
            # 将编译时间加入登录提示
            echo "Built in `date "+%Y%m%dT%H%M%S%z"`" >> /etc/motd; \\
            # 将环境变量写到/etc/profile里面，保证SSH登录的时候能够正确使用
            # 执行编译脚本
            sh /tmp/${{builder_sh}}; \\
            # 删除编译脚本
            rm -f /tmp/${{builder_sh}}; \\
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

        content_str = '\n'.join([ l[8:] if l.startswith(' '*8) else l for l in content_str.split('\n') if l])
        return content_str


try:
    coder = ShCoder(None, *[ e for e in GroupDefs.__members__ ])
    coder.load_configuration(PKG_INFO_STR)

    with tempfile.TemporaryDirectory() as build_tmp_dir:
        with tempfile.NamedTemporaryFile(mode='w+', dir=build_tmp_dir) as dockerfile_f:
            with tempfile.NamedTemporaryFile(mode='w+', dir=build_tmp_dir) as software_script_f:
                dockerfile_f.write(coder.get_dockerfile_content())
                dockerfile_f.flush()

                software_script_f.write(coder.get_software_script_content())
                software_script_f.flush()

                cmdline = ' '.join([
                    'docker',
                    'build',
                    '--force-rm',
                    # '--pull',
                    '--no-cache',
                    '--build-arg HTTP_PROXY=${HTTP_PROXY}',
                    '--build-arg HTTPS_PROXY=${HTTPS_PROXY}',
                    f'--build-arg builder_sh={os.path.basename(software_script_f.name)}',
                    f'-t {coder.name}:latest',
                    f'-f {dockerfile_f.name}',
                    build_tmp_dir
                ])
                print(f'Command: {cmdline}')
                
                # if subprocess.call(f'docker build {" ".join(cmdline_opts)} .', shell=True):
                #     print("Build image failed")
                if subprocess.call(cmdline, shell=True, cwd=build_tmp_dir):
                    print("Build image failed")

                software_script_f.seek(0)
                dockerfile_f.seek(0)

                print(coder.get_software_script_content())
                print(coder.get_dockerfile_content())

    # shutil.rmtree(build_tmp_dir, ignore_errors=True)
    # os.removedirs(tmpdir)
except BaseException as e:
    warnings.warn(e)

