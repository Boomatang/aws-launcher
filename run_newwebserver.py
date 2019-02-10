import click
import boto3
import botocore

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
def cli():
    """Get extra help on commands by COMMAND --help"""
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
    click.echo(f'Create EC2 instance, {name} in group {group}')

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

    if group is not None:
        tag = create_tag('Group', group)
        tag_specifications['Tags'].append(tag)

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

    if len(security_group) > 0:
        config['SecurityGroups'] = security_group

    ec2 = boto3.resource('ec2')
    instance = ec2.create_instances(**config)

    result = f"Created EC2 instance.\n\tID: {instance[0].id}\n\tCurrent State: {instance[0].state['Name']}"
    click.echo(result)


@click.command()
def webserver():
    click.echo('Deploys the web server script')


@click.command()
@click.confirmation_option(prompt="Are you sure you want to terminate instances")
@click.option('--group', envvar='GROUP', help="Group the instances belongs too.")
@click.option('-a', '--all', is_flag=True, help="Select all instances. Protected instances will not be terminated")
def destroy(group, all):
    """Terminate EC2 instances"""
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
        try:
            click.echo(f'Terminating {name}')
            i.terminate()
        except Exception as err:
            click.echo(f'Issue terminating {name}')


@click.command()
@click.option('--name', '-n', help="Name of instance")
@click.option('--group', '-g', help="Group the instance belongs too.")
@click.option('--all', '-a', is_flag=True, help="Get status of all instances")
def status(name, group, all):
    """Gets the status of existing EC2 instances"""

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
cli.add_command(webserver)
cli.add_command(destroy)
cli.add_command(status)

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
def bucket(name, location):
    """Create a S3 bucket.\n
    """
    s3 = boto3.client('s3')

    config = {
        'Bucket': name,
        'CreateBucketConfiguration': {
            'LocationConstraint': location
        }
    }
    try:
        response = s3.create_bucket(**config)

        print(response)

    except s3.exceptions.BucketAlreadyExists as error:
        click.echo(f'Bucket name <{name}> already exists')

    except s3.exceptions.ClientError as error:
        click.echo('There is an error with the name used.')


@click.command()
@click.argument('bucket', required=True)
@click.argument('filename', required=True, type=click.File('r'))
def add_file():
    """Upload a give file to stated S3 bucket"""


@click.command()
@click.argument('bucket', required=True)
@click.option('--empty', help='Removes contains of bucket before removing bucket')
@click.confirmation_option(prompt="Remove S3 bucket...")
def remove_bucket():
    """Removes a S3 bucket"""


@click.command()
def list_buckets():
    """Lists all the buckets that the user has access too."""

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

    if error_count:
        braker = '*'*18
        message = f'\t{braker}\n\t{error_count} errors happened.\n\t{braker}'

        click.echo(message)


cli.add_command(bucket)
cli.add_command(add_file)
cli.add_command(remove_bucket)
cli.add_command(list_buckets)

if __name__ == '__main__':
    cli()
