# aws-launcher
Developer Operations Assignment 1

This project requires python 3.6 or higher.
Set up was done using pipenv.

## Usage
* add-file , Upload a given file to a stated S3 bucket
* add-image , Adds a image to a S3 buket and create an index page on a EC2 instances
* bucket , Create a S3 bucket
* check-web-server , Checks if httpd is running on the server
* create , Create an EC2 instances
* delete-bucket , Deletes a S3 bucket
* destroy , Terminates EC2 instances.
* list-buckets , Lists all the buckets that the user has access too.
* status , Gets the status of existing EC2 instances

All the main functions have flags that can be added. You can learn move by doing \[COMMAND\] --help

There is a set of system variables that can be set.
* KEYNAME , The default key to be used
* KEYLOCATION , Path to where keys are stored
* SECURITYGROUP , A list of security groups to be added to an instance
* GROUP , A tag that will be give to instances. It is possible to filter by group or name of instances

### Typical Work Flow
For this a assignment this is the typical steps that are required.
1. Create an EC2 instances: `python run_newwebserver.py create --name test_server`
2. Create a S3 bucket: `python run_newwebserver.py bucket --name unique_name`
3. Get status of EC2 instances, you need the ID and Public dns for later steps: `python run_newwebserver.py status --name test_server`
4. Check web server. This will try fix any errors that happen including installing python if required: `python run_newwebserver.py check-web-server --id I-#########`
5. Add image to S3 bucket and create an index.html file on the web server: `python run_newwebserver.py add-image --image image_name.png --server-id I-######## --bucket unique_bucket`
6. Use the instance Public dns in a web browser to view the image. Address was gotten in step 3.

## Used Packages
[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

[click](https://click.palletsprojects.com/en/7.x/)

[Loguru](https://github.com/Delgan/loguru)
