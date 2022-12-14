# Advanced: Running Remotely on a Server   
If you only want to run our your own computer, you can ignore these instructions.    

The following are instructions for setting up the annotation tool on a remote server i.e. not on a local computer, but in the cloud. Tested with `gunicorn==19.7.1`.    
```
# install python
wget https://repo.anaconda.com/archive/Anaconda3-2019.03-Linux-x86_64.sh
bash Anaconda3-2019.03-Linux-x86_64.sh
export PATH=~/anaconda3/bin:$PATH
```
```
# setup websever
conda install gunicorn
sudo apt-get install nginx
sudo rm /etc/nginx/sites-enabled/default
```

Edit the nginx config file so it contains the info in the brackets.
```
sudo nano  /etc/nginx/sites-available/example.com

"""
server {
        listen 80;

        location / {
                proxy_pass http://127.0.0.1:8000/;
        }
}
"""
sudo ln -s /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/example.com
```

```
# download the annotation code from this repo
mkdir audio_annotation_app
cd audio_annotation_app
git clone ...
```

```
# run annotation app
sudo service nginx restart
screen gunicorn application:application
```
