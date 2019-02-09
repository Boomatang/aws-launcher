import click
import boto3

def get_tag_value(tags, name):
    '''Get a tag value from a list of tags'''
    for tag in tags:
        if tag['Key'] == name:
            return tag['Value']
    return None

@click.group()
def cli():
    '''Get extra help on commands by COMMAND --help'''
    pass

@click.command()
@click.option('--name', help="Name of instance")
@click.option('--group', envvar='GROUP', help="Group the instance belongs too.")
def create(name, group):
    click.echo(f'Create EC2 instance, {name}')
    click.echo(group)

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
        name = get_tag_value(i.tags, 'Name')
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
