### Grand Rapids Accident Data Viz
The purpose of this app is to test deployment of a Plotly Dash 
app on AWS Elastic Beanstalk with Snwoflake database connection.  Each interaction
triggers a query to retreive aggregate data from a Snowflake database.

Application URL:
https://grcrash.swtally.com/

##### Database Credentials
To avoid embedding credentials in code, they are stored in OS environment variables.
These variables are configured in the AWS Elastic Beanstalk environment configuration software category.
For local development, use the following code to set enviromnet variables:

os.environ['SNOWFLAKE_USER'] = 'USERNAME'  
os.environ['SNOWFLAKE_PWD'] = 'PASSWORD'  
os.environ['SNOWFLAKE_WAREHOUSE'] = 'WAREHOUSE NAME'


##### Deployment
1. run the following command to zip application Python file and requirements.txt together
into dash_application zip file
    zip dash_application.zip requirements.txt application.py
    
2. Upload zip file to Elastic Beanstalk admin console