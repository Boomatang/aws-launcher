import click
import boto3

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
    '''Get extra help on commands by COMMAND --help'''
    pass

@click.command()
@click.option('--name', '-n', help="Name of instance")
@click.option('--group', '-g', envvar='GROUP', help="Group the instance belongs too.")
@click.option('--max_count', default=1, help="Max count of instances")
@click.option('--min_count', default=1, help="Min count of instances")
@click.option('--key_name', '-k', envvar='KEYNAME', help="Key name used for SSH")
@click.option('--security_group', '-s', envvar='SECURITYGROUP', multiple=True, help="List of security groups to be assigned to the instances")
def create(name, group, max_count, min_count, key_name, security_group):
    '''Create an EC2 instance'''
    click.echo(f'Create EC2 instance, {name} in group {group}')
    
    tag_specifications = {
            'ResourceType': 'instance',
            'Tags': []
            }

    if name is not None:
        tag = create_tag('Name', name)
        tag_specifications['Tags'].append(tag)

    if group is not None:
        tag = create_tag('Group', group)
        tag_specifications['Tags'].append(tag)
    
    TagSpecifications = [tag_specifications,]
    config = {
            'ImageId': 'ami-0fad7378adf284ce0',
            'MinCount': min_count,
            'MaxCount': max_count,
            'InstanceType': 't2.micro',
            'TagSpecifications': TagSpecifications
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
def stop():
    click.echo('Stops an EC2 instance')

@click.command()
@click.confirmation_option(prompt="Are you sure you want to termainate instances")
@click.option('--group', envvar='GROUP', help="Group the instances belongs too.")
@click.option('--all', is_flag=True, help="Select all instances. Protected instances will not be termainated")
def destroy(group, all):
    '''Termainate S3 instances'''
    click.echo('Termainates an instance')
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
            click.echo(f'Termainating {name}')
            i.terminate()
        except Exception as err:
            click.echo(f'Issue termainating {name}')

cli.add_command(create)
cli.add_command(webserver)
cli.add_command(stop)
cli.add_command(destroy)

if __name__ == '__main__':
    cli()
