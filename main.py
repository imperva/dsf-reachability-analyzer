import boto3
import time
import json

# Create a session with the specified AWS access key and secret key
session = boto3.Session(
    aws_access_key_id='AKIARUGULLAY4R4YGN3G',
    aws_secret_access_key='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',
    region_name='eu-west-3'
)



# Create a client to the Global Accelerator service
client = session.client('ec2')

# Specify the source and destination IP addresses
# source='eni-07e760710fa0a7d09'
# destination='eni-0d94f19d7a00ed1a5',


# Create a network insights path
response_create = client.create_network_insights_path(
    Source='eni-07e760710fa0a7d09',
    Destination='eni-0d94f19d7a00ed1a5',
    Protocol='tcp',
    # DestinationPort=22
    DestinationPort=8080
    # DestinationPort=8443
    # DestinationPort=3030
    # DestinationPort=27117

)
print("NetworkInsightsPathId: " + response_create['NetworkInsightsPath']['NetworkInsightsPathId'])


response_start = client.start_network_insights_analysis(
    NetworkInsightsPathId=response_create['NetworkInsightsPath']['NetworkInsightsPathId']
)

print("NetworkInsightsAnalysisId: " + response_start['NetworkInsightsAnalysis']['NetworkInsightsAnalysisId'])
response_describe = None
status = None
while True:


    response_describe = client.describe_network_insights_analyses(
        NetworkInsightsAnalysisIds=[
            response_start['NetworkInsightsAnalysis']['NetworkInsightsAnalysisId'],
        ])
    status = response_describe['NetworkInsightsAnalyses'][0]['Status']
    print(status)
    time.sleep(5.5)
    if status != 'running':
        break

    


network_path_found = response_describe['NetworkInsightsAnalyses'][0]['NetworkPathFound']


# Print the details of the path

# print(response_create)
print("----------------")
print("Test: " + status)
print("Network: " + str(network_path_found))
print("Details ************")
# print (json.dumps(response_describe, indent=4, sort_keys=True, default=str))
