import json
import os
import time
import digitalocean
import paramiko
import requests

manager = digitalocean.Manager(token="fbc8b80bf5f1a1f6301ae9e2ca677f1a1742e53f968f0f0ff7c4d3e23cb9f556")

############################ Misc  info ############################
identifier = 'IDENTIFIER FOR WHMCS'
secret = 'WHMCS SECRET'
url = 'WHMCS API ACCESS POINT'
sshpass = 'SSH PASSWORD'
DOtoken= 'DIGITALOCEAN TOKE'
theme_url = 'https://aguilaair.tech/theme.zip' 
theme_name = 'theme.zip'
####################################################################


def generateurl(actions):
    urlbuilt = url + '?action=' + actions + "&username=" + identifier + '&password=' + secret + '&responsetype=json'
    return urlbuilt


print('Run Started!')

r = requests.post(generateurl('GetClientsProducts'))

whmcs_raw = json.loads(r.text)

my_droplets = manager.get_all_droplets(tag_name='pending')

time.sleep(600)

for i in range(0, len(whmcs_raw["products"]["product"])):
    whmcs_servid = whmcs_raw["products"]["product"][i]['customfields']['customfield'][0]['value']
    whmcs_pass = whmcs_raw["products"]["product"][i]["password"]
    for o in range(0, len(my_droplets)):
        selected_droplet = str(my_droplets[o])
        if selected_droplet.find(whmcs_servid) != -1:
            droplet = digitalocean.Droplet(token=DOtoken,
                                           id=whmcs_servid)
            ldroplet = droplet.load()
            ip = ldroplet.ip_address
            response = os.system('ping -c 1 ' + ip)
            print(ip)
            if response == 0:
                try:
                    print('SSHing into droplet...')
                    ssh = paramiko.client.SSHClient()
                    keyfile = 'ssh/SSH'
                    k = paramiko.RSAKey.from_private_key_file(keyfile, password=sshpass)
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ip, username='IonisedHostingAdmin', pkey=k)

                    print('Setting Plesk admin Password...')
                    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                        "sudo plesk bin admin --set-admin-password -passwd '" + whmcs_pass + "'", get_pty=True)
                    for line in iter(ssh_stdout.readline, ''):
                        print(line)

                    print('Grabbing theme for Plesk...')
                    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo wget ' + theme_url,
                                                                         get_pty=True)
                    for line in iter(ssh_stdout.readline, ''):
                        dl_attempt = True

                    print('Installig Plesk theme')
                    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
                        'sudo plesk bin branding_theme -i -vendor admin -source ' + theme_name, get_pty=True)
                    for line in iter(ssh_stdout.readline, ''):
                        print(line)

                    print('Changing droplet status')
                    ssh.close()
                    tag = digitalocean.Tag(name="READY",
                                           token=DOtoken)
                    tag.create()
                    tag.add_droplets(whmcs_servid)
                    tag = digitalocean.Tag(name="pending",
                                           token=DOtoken)
                    tag.remove_droplets(whmcs_servid)
                    print('Done processing droplet. Going to the next one...')
                except:
                    print('Error when attempting to SSH into droplet' + whmcs_servid)
                    continue
            else:
                print('Host was unresponsive, skipping')
        else:
            print('Droplet ' + whmcs_servid + ' not found or already provisioned!')

print('Run completed!')
