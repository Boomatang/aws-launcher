import os
import subprocess
from pathlib import Path
import click
import boto3
import botocore
import sys

# ------------ Setting up the logging -----------
from loguru import logger

logger.add("info.log", rotation="10 MB", format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", level='INFO')
logger.add("errors.log", rotation="10 MB", format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}")
# Remove the logging print out to standard error
# logger.remove(0)

# logger.add(sys.stdout, format="<green>{time}</green> | <level>{message}</level>")

# ------------ Working with EC2 -----------------


def get_tag_value(tags, name):
    '''Get a tag value from a list of tags'''
    for tag in tags:
        if tag['Key'] == name:
            return tag['Value']
    return None


def create_tag(key, value):
    output = {
        'Key': key,
        'Value': value
    }
    return output


@click.group()
@logger.catch
def cli():
    """Get extra help on commands by COMMAND --help"""
    logger.info('App started')
    pass


@click.command()
@click.option('--name', '-n', help="Name of instance")
@click.option('--group', '-g', envvar='GROUP', help="Group the instance belongs too.")
@click.option('--max_count', default=1, help="Max count of instances")
@click.option('--min_count', default=1, help="Min count of instances")
@click.option('--key_name', '-k', envvar='KEYNAME', help="Key name used for SSH")
@click.option('--security_group', '-s', envvar='SECURITYGROUP', multiple=True,
              help="List of security groups to be assigned to the instances")
def create(name, group, max_count, min_count, key_name, security_group):
    """Create an EC2 instance"""
    message = f'Create EC2 instance, {name} in group {group}'
    click.echo(message)
    logger.info(message)

    tag_specifications = {
        'ResourceType': 'instance',
        'Tags': []
    }

    user_data = '#!/bin/bash\n' \
                'yum update -y\n' \
                'yum install httpd -y\n' \
                'systemctl enable httpd\n' \
                'systemctl start httpd'

    if name is not None:
        tag = create_tag('Name', name)
        tag_specifications['Tags'].append(tag)
    else:
        logger.degug("No tag Name was set")

    if group is not None:
        tag = create_tag('Group', group)
        tag_specifications['Tags'].append(tag)
    else:
        logger.dedug('No Group tag was set')

    TagSpecifications = [tag_specifications, ]
    config = {
        'ImageId': 'ami-0fad7378adf284ce0',
        'MinCount': min_count,
        'MaxCount': max_count,
        'InstanceType': 't2.micro',
        'TagSpecifications': TagSpecifications,
        'UserData': user_data
    }

    if key_name is not None:
        config['KeyName'] = key_name
    else:
        logger.degug("No KeyName was set")

    if len(security_group) > 0:
        config['SecurityGroups'] = security_group
    else:
        logger.degug("No Security Grounp was set")

    ec2 = boto3.resource('ec2')
    instance = ec2.create_instances(**config)

    result = f"Created EC2 instance.\n\tID: {instance[0].id}\n\tCurrent State: {instance[0].state['Name']}"
    click.echo(result)
    logger.info(result)


@click.command()
@click.confirmation_option(prompt="Are you sure you want to terminate instances")
@click.option('--group', envvar='GROUP', help="Group the instances belongs too.")
@click.option('-a', '--all', is_flag=True, help="Select all instances. Protected instances will not be terminated")
def destroy(group, all):
    """Terminate EC2 instances"""
    logger.info('Destroy function called')

    click.echo('Terminates an instance')
    ec2 = boto3.resource('ec2')
    if all:
        instances = ec2.instances.all()
    else:
        instances = ec2.instances.filter(
            Filters=[
                {
                    'Name': 'tag:Group',
                    'Values': [group],
                }
            ]
        )

    for i in instances:
        try:
            name = get_tag_value(i.tags, 'Name')
        except TypeError:
            name = "Undefined"
            logger.exception('Type Error : No tag Name')
        try:
            click.echo(f'Terminating {name}')
            i.terminate()
        except Exception as err:
            click.echo(f'Issue terminating {name}')
            logger.exception('Destroy Exception')


@click.command()
@click.option('--name', '-n', help="Name of instance")
@click.option('--group', '-g', help="Group the instance belongs too.")
@click.option('--all', '-a', is_flag=True, help="Get status of all instances")
def status(name, group, all):
    """Gets the status of existing EC2 instances"""
    logger.info('Status function called')
    ec2 = boto3.resource('ec2')
    instances = None
    if all:
        instances = ec2.instances.all()
    elif group:
        instances = ec2.instances.filter(
            Filters=[
                {
                    'Name': 'tag:Group',
                    'Values': [group],
                }
            ]
        )
    elif name:
        instances = ec2.instances.filter(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [name],
                }
            ]
        )
    else:
        click.echo("You must set '--name', '--group' or '--all'", err=True)

    if instances is not None:
        click.echo('Getting status of instance(s)')
        for i in instances:

            id_ = i.id
            state = i.state['Name']
            key_name = i.key_name
            public_dns_name = i.public_dns_name

            try:
                name = get_tag_value(i.tags, 'Name')
            except TypeError:
                name = "Not Set"

            try:
                group = get_tag_value(i.tags, 'Group')
            except TypeError:
                group = "Not Set"

            result = f"\n" \
                f"\tID: {id_}\n" \
                f"\tState: {state}\n" \
                f"\tName: {name}\n" \
                f"\tGroup: {group}\n" \
                f"\tKey Pair: {key_name}\n" \
                f"\tPublic dns: {public_dns_name}\n"

            click.echo(result)

    else:
        click.echo('No instances found')


cli.add_command(create)
cli.add_command(destroy)
cli.add_command(status)

# ------------ Working with web server-----------------


def get_instances(instances):
    """
    Gets the instances of a machine
    :param instances: String Id of machine
    :return: boto3.instance
    """
    logger.info("Getting machine instance (Function call)")
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instances)

    return instance


def get_key_pair_path(key_path, key_pair):
    extension = '.pem'

    key = Path(key_path, key_pair + extension)

    if key.is_file():
        return str(key)
    else:
        raise FileNotFoundError


def install_python37(key, ip):
    """Install python3.7"""
    actions = ['sudo yum update -y', 'sudo yum install -y python37']

    base_command = f"ssh -t -o StrictHostKeyChecking=no -i {key} ec2-user@{ip} \'"

    click.echo("Updating and installing python")
    logger.info(f"Updating and installing python on {ip}")
    for action in actions:
        command = base_command + action + "\'"

        response = subprocess.run(command, shell=True)
        print(response)


def copy_file_to_server(key, ip, filename="check_webserver.py"):
    """Copy a file to the server"""

    command = f"scp -i {key} {filename} ec2-user@{ip}:/home/ec2-user "
    print(command)

    click.echo(f"Coping {filename} to server")
    logger.info(f"Coping {filename} to {ip}")
    response = subprocess.run(command, shell=True)
    print(response)


@click.command()
@click.option('-i', '--id', 'machine', required=True, help='The Id number for the machine where the server is deployed')
def check_web_server(machine):
    """
    Checks if httpd is running on the server.
    If there is no test script this is copied to the server.
    :return:
    """
    logger.info("Web server been checked")

    click.echo('Deploys the web server script')

    # get machine instances
    instance = get_instances(machine)

    # get instances public ip
    ip = instance.public_ip_address

    # get instances key pair
    key_pair = instance.key_name

    # get standard key pair location
    key_path = os.environ.get('KEYLOCATION')
    if key_path is None:
        click.echo('System variable most be set : KEYLOCATION')
        logger.debug('No KEYLOCATION variable set')

    key_pair_path = get_key_pair_path(key_path, key_pair)

    # try run web server checker
    command = f"ssh -t -o StrictHostKeyChecking=no -i {key_pair_path} ec2-user@{ip} \'python3 check_webserver.py\'"

    tries = 3
    logger.debug(command)
    while tries > 0:
        status = subprocess.run(command, shell=True)
        if status.returncode == 0:
            break

        if status.returncode == 127:
            install_python37(key_pair_path, ip)

        if status.returncode == 2:
            copy_file_to_server(key_pair_path, ip)

        tries -= 1
    else:
        click.echo("Unknown issue with checking server")
        logger.debug("Checking server timed out on tries. Unknown reason")


def create_index_file(image_details):
    """Creates a index.html file on the locale disc to be copied up to the server"""

    data = f'''
    <html>
    <head>
    <title>Sample Index Page</title>
    </head>
    <body>
    <img src="{image_details}">
    </body>
    </html>
    '''

    with open('index.html', 'w+') as f:
        f.write(data)


def move_file(key_pair_path, ip, filename, src, dst):
    """Moves a file a server to a different location """

    command = f"ssh -t -o StrictHostKeyChecking=no -i {key_pair_path} ec2-user@{ip} \'sudo mv {filename} {dst}\'"

    print(command)
    subprocess.run(command, shell=True)
    click.echo(f'{filename} has been place in {dst}.')


@click.command()
@click.option('-i', '--image', required=True, help="Image file to be uploaded")
@click.option('-s', '--server-id', 'server', required=True, help="Server Id that the image is to be shown on")
@click.option('-b', '--bucket', 'bin', required=True, help="Bucket to where the image is to be loaded")
def add_image(image, server, bin):
    """Adds a image a S3 bucket and creates an index page on the server to display the image \f"""
    logger.info("Add image to web server to be displayed")

    response = _add_file(filename=image, bucket=bin, public_read=True)

    if response:
        image_path = f"https://s3-eu-west-1.amazonaws.com/{bin}/{image}"
        create_index_file(image_path)

        # TODO this should be refactored, its copied and pasted from above
        instance = get_instances(server)

        # get instances public ip
        ip = instance.public_ip_address

        # get instances key pair
        key_pair = instance.key_name

        # get standard key pair location
        key_path = os.environ.get('KEYLOCATION')
        if key_path is None:
            click.echo('System variable most be set : KEYLOCATION')
            logger.debug('No KEYLOCATION variable set')

        key_pair_path = get_key_pair_path(key_path, key_pair)
        copy_file_to_server(key_pair_path, ip, filename='index.html')

        config = {
            'key_pair_path': key_pair_path,
            'ip': ip,
            'filename': 'index.html',
            'dst': '/var/www/html/index.html',
            'src': '.'
            }
        move_file(**config)

        # get the server ip address
        # create the html file
        # copy file to server
        # launch web browser


cli.add_command(check_web_server)
cli.add_command(add_image)

# ------------ Working with S3 -----------------


def item_counter(bucket):
    """Counts the number of items in a bucket"""
    count = 0

    for _ in bucket.objects.all():
        count += 1

    return count


@click.command()
@click.option('-n', '--name', required=True, help="Name of bucket, should be a globally unique name.")
@click.option('-l', '--location', default='eu-west-1', show_default=True, help="Sets location to deploy the bucket")
@click.option('--public-read', 'public_read', is_flag=True, help="Set bucket to have public reads")
def bucket(name, location, public_read):
    """Create a S3 bucket.
    """
    logger.info('Create bucket function called')

    s3 = boto3.client('s3')

    config = {
        'Bucket': name,
        'CreateBucketConfiguration': {
            'LocationConstraint': location
        },
    }

    if public_read:
        config['ACL'] = 'public-read'

    try:
        response = s3.create_bucket(**config)

        click.echo("Your bucket has been created")
        # print(response)

    except s3.exceptions.BucketAlreadyExists as error:
        click.echo(f'Bucket name <{name}> already exists')
        logger.excetion('Bucket Already Exists')
    except s3.exceptions.ClientError as error:
        print(error)
        logger.excetion('Unknown Error')


@click.command()
@click.option('-b', '--bucket', required=True, help="Bucket to store the file in.")
@click.option('-f', '--file-name', 'filename', required=True, help="Name of file to uploaded")
@click.option('--public-read', 'public_read', is_flag=True, help="Allows public read of file")
def add_file(filename, bucket, public_read):
    """Upload a give file to stated S3 bucket"""
    logger.info('Add file to bucket')

    if public_read:
        access = True
    else:
        access = False

    _add_file(filename, bucket, public_read=access)


def _add_file(filename, bucket, public_read):
    client = boto3.client('s3')

    config = {
        'Bucket': bucket,
        'Key': filename
    }
    try:
        with open(filename, 'rb') as f:
            config['Body'] = f.read()
    except FileNotFoundError as error:
        click.echo(error)
        logger.exection('No file found')

    if public_read:
        config['ACL'] = 'public-read'
        logger.debug('ACL set to public read')

    if 'Body' in config.keys():
        try:
            client.put_object(**config)
            click.echo(f"File has been uploaded to S3 bucket {bucket}")
            return True
        except Exception as error:
            logger.exection('Error uploading')
            print(error)
            return False
    else:
        return False


@click.command()
@click.option('-n', '--name', required=True, help="Name of bucket to be deleted")
@click.option('-e', '--empty-bucket', 'empty', is_flag=True, help='Removes contains of bucket before removing bucket')
@click.confirmation_option(prompt="Remove S3 bucket...")
def delete_bucket(name, empty):
    """Deletes a S3 bucket"""
    logger.info('Delete bucket function called')
    s3 = boto3.client('s3')

    if empty:
        try:
            bucket = boto3.resource('s3').Bucket(name)
            for key in bucket.objects.all():
                response = key.delete()
            click.echo("Bucket contains have been removed.")
        except s3.exceptions.NoSuchBucket as error:
            click.echo(f"No such bucket called {name}")
            logger.excetion("No Such Bucket ({name}) found")
            return

    try:
        s3.delete_bucket(Bucket=name)
        click.echo(f'Bucket {name} has been deleted')
    except s3.exceptions.NoSuchBucket as error:
        click.echo(f"No such bucket called {name}")
        logger.excetion("No Such Bucket ({name}) found")
    except s3.exceptions.ClientError as error:
        logger.excetion("A Client Error happened")
        click.echo(f'Please see --help for more help')


@click.command()
def list_buckets():
    """Lists all the buckets that the user has access too."""
    logger.info("Listing all buckets function called")
    click.echo("Listing buckets")

    s3 = boto3.resource('s3')

    error_count = 0

    for bucket in s3.buckets.all():
        try:
            name = bucket.name
            item_count = item_counter(bucket)

            result = f'\n' \
                f'\tBucket: {name}\n' \
                f'\tNo. of Items: {item_count}\n'

            click.echo(result)

        except Exception as error:
            error_count += 1
            # print(error)
            # logger adds a lot of information that is not helpfuly
            # logger.exception("Error reading bucket {bucket}")
            logger.error("Error reading bucket")

    if error_count:
        line_brake = '*'*18
        message = f'\t{line_brake}\n\t{error_count} errors happened.\n\t{line_brake}'
        logger.debug(message)
        click.echo(message)


cli.add_command(bucket)
cli.add_command(add_file)
cli.add_command(delete_bucket)
cli.add_command(list_buckets)

if __name__ == '__main__':
    cli()
