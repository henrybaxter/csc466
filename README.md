## Python

Install and setup pyenv (so you can easily pick Python versions)

    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile

Restart your terminal, then install 3.6.0

    pyenv install 3.6.0

## SSH

Edit your SSH config

    vim ~/.ssh/config

So that it includes

    Host csc466-router
        HostName csc466-router.baxtergroup.io
        User ubuntu
        IdentityFile ~/.ssh/csc466_id_rsa

    Host csc466-server
        HostName csc466-server.baxtergroup.io
        User ubuntu
        IdentityFile ~/.ssh/csc466_id_rsa

Ensure you have csc466_id_rsa, that it's in this location, and the permissions are correct:

    chmod 600 ~/.ssh/csc466_id_rsa

## Source code

Assume you have a `~/projects` directory, replace with similar

    git clone git@github.com:henrybaxter/csc466.git ~/projects/

## Python libraries

    cd ~/projects/csc466
    pip install -r requirements.txt

## QUIC Certificate

Open Keychain Access and drag and drop `~/projects/csc466/2048-sha256-root.pem` into it, then right click and hit **Get Info**. Change to **Always Trust**.

![Import Root CA](screenshots/import-root-ca.png?raw=true "Importing the Root CA in Keychain Access")
