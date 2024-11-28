# XRFitVis

Web-based visualization of XRF maps, compatible with PyMCA fit output and other fitting tools.

Live publicly available XRFitVis service on: https://vuo.elettra.eu/go/xrfitvis 

## Setup

The software can be installed on your local server

#### Setup anacoda, miniconda, mamba or micromamba

[Skip to "Download and run" if not needed]

For micromamba:

```bash
# download micromamba and run the installer
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
# init the micromamba python framework
./bin/micromamba shell init -s bash -r ~/micromamba  # this writes to your .bashrc file
```

After the micromamba init, your `.bashrc` file should look like this: 

```bash
# >>> mamba initialize >>>
# !! Contents within this block are managed by 'mamba init' !!
export MAMBA_EXE='/home/your_user/.local/bin/micromamba';
export MAMBA_ROOT_PREFIX='/home/your_user/micromamba';
__mamba_setup="$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX" 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__mamba_setup"
else
    alias micromamba="$MAMBA_EXE"  # Fallback on help from mamba activate
fi
unset __mamba_setup
# <<< mamba initialize <<<
```

Now you can create your Python environment and activate it with:

```bash
micromamba create -n xrffitvis -c conda-forge numpy scipy scikit-image scikit-learn h5py matplotlib pandas seaborn requests nicegui opencv tifffile python-dotenv
conda activate xrffitvis
```

## Download and run

Download the XRFitVis software with:

```bash
git clone https://github.com/ElettraSciComp/XRFitVis
cd XRFitVis
```

and lunch it with:

```bash
python xrfmain.py
```

You can change the port where the application is served and eventually setup your nginx server by adding this proxypass solver to the `/etc/nginx/sites-available/default` file (in the `server{` portion)

```nginx
    location ~ ^/xrfitvis/(.*)$ {
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header Authorization $http_authorization;
            proxy_pass_header Authorization;
            proxy_set_header Host $http_host;
            #proxy_socket_keepalive on ;
            proxy_pass http://127.0.0.1:8228/$1?$args;
            proxy_set_header X-Forwarded-Prefix /xrfitvis;
            proxy_redirect  http://127.0.0.1:8228/ /xrfitvis/;
        }
```

Then navigate to `http://localhost/xrfitvis` and you should see the main web interface running
