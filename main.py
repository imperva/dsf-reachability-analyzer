import boto3
import time
import json



def init_client():
    # Create a session with the specified AWS access key and secret key
    session = boto3.Session(
        aws_access_key_id='AKIARUGULLAY4R4YGN3G',
        aws_secret_access_key='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',
        region_name='eu-west-3'
    )

    client = session.client('ec2')
    return client


def create_network_insights_path(source, destination,port):
    response_create = client.create_network_insights_path(
        Source=source,
        Destination=destination,
        Protocol='tcp',
        DestinationPort=port
        # DestinationPort=22
        # DestinationPort=8080
        # DestinationPort=8443
        # DestinationPort=3030
        # DestinationPort=27117

    )
    print("NetworkInsightsPathId: " + response_create['NetworkInsightsPath']['NetworkInsightsPathId'])
    network_insights_path_id = response_create['NetworkInsightsPath']['NetworkInsightsPathId']
    return network_insights_path_id


# response_create['NetworkInsightsPath']['NetworkInsightsPathId']
def start_network_insights_analysis(network_insights_path_id):
    response_start = client.start_network_insights_analysis(
        NetworkInsightsPathId=network_insights_path_id
    )

    analysis_id = response_start['NetworkInsightsAnalysis']['NetworkInsightsAnalysisId']
    print("NetworkInsightsAnalysisId: " + analysis_id)
    return analysis_id


def fetch_network_insights_analyses_result(analysis_id):    
    response_describe = None
    status = None
    while True:
        response_describe = client.describe_network_insights_analyses(
            NetworkInsightsAnalysisIds=[
                analysis_id,
            ])
        status = response_describe['NetworkInsightsAnalyses'][0]['Status']
        print(status)
        time.sleep(5.5)
        if status != 'running':
            break

    network_path_found = response_describe['NetworkInsightsAnalyses'][0]['NetworkPathFound']
    return status, network_path_found


subnet1 = input("Subnet1:") 
subnet2 = input("Subnet2:") 
analyze_bi_direction = input("Analizy bi-direction (y/n):")
analyze_specific_ports = input("Analizy specific ports (list coma delimited):")

if analyze_specific_ports == '':
    analyze_specific_ports = "22,8080,8443,3030,27117"

analyze_specific_ports_list = list(analyze_specific_ports.split(","))
        # DestinationPort=22
        # DestinationPort=8080
        # DestinationPort=8443
        # DestinationPort=3030
        # DestinationPort=27117


def analyze(subnet1, subnet2, bi_direction, analyze_specific_ports_list):
    # Create eni in subnet1
    subnet1_eni ='eni-07e760710fa0a7d09'
    # Create eni in subnet2
    subnet2_eni = 'eni-0d94f19d7a00ed1a5'

    analyzation_result = {
        "full_network_path_found" : True,
        "path_info" : []  
    }
    
    # results = []
    for port in analyze_specific_ports_list:
        port = int(port)
        status, network_path_found = fetch_network_insights_analyses_result(start_network_insights_analysis(create_network_insights_path(subnet1_eni, subnet2_eni, port)))
        if analyzation_result["full_network_path_found"] != False:
            analyzation_result["full_network_path_found"] = network_path_found
        path_result = {
            "network_path_found" : network_path_found,
            "source": subnet1_eni,
            "destination": subnet2_eni,
            "port": port
        }
        analyzation_result["path_info"].append(path_result)
    return analyzation_result

client = init_client()
analyzation_list = analyze(subnet1,subnet2,analyze_bi_direction,analyze_specific_ports_list)

print(analyzation_list)


# Print the details of the path

# # print(response_create)
# print("----------------")
# print("Test: " + status)
# print("Network: " + str(network_path_found))
# print("Details ************")
# # print (json.dumps(response_describe, indent=4, sort_keys=True, default=str))
