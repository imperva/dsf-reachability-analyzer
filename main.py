import boto3
import time
import json

def init_client(access_key,secret_key,region):
    # Create a session with the specified AWS access key and secret key
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )

    client = session.client('ec2')
    return client


def create_network_insights_path(source, destination,port):
    response_create = client.create_network_insights_path(
        Source=source,
        Destination=destination,
        Protocol='tcp',
        DestinationPort=port,
         TagSpecifications=[
            {
                'ResourceType': 'network-insights-path',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': source + "->" + destination + " :" + str(port)
                    }
                ]
            }]
    )
    network_insights_path_id = response_create['NetworkInsightsPath']['NetworkInsightsPathId']
    prints("Network Insight Path Created. NetworkInsightsPathId: " + network_insights_path_id)

    
    return response_create['NetworkInsightsPath']

def start_network_insights_analysis(network_insights_path_id):
    response_start = client.start_network_insights_analysis(
        NetworkInsightsPathId=network_insights_path_id
    )

    analysis_id = response_start['NetworkInsightsAnalysis']['NetworkInsightsAnalysisId']
    prints("Network Analisys Started. NetworkInsightsAnalysisId: " + analysis_id)

    return response_start['NetworkInsightsAnalysis']


def fetch_network_insights_analyses_result(analysis_id):    
    response_describe = None
    status = None
    while True:
        response_describe = client.describe_network_insights_analyses(
            NetworkInsightsAnalysisIds=[
                analysis_id,
            ])
        status = response_describe['NetworkInsightsAnalyses'][0]['Status']
        prints("Waiting for Analysis completion. Status: "  + status)
        time.sleep(5)
        if status != 'running':
            break
    
    full_info = response_describe['NetworkInsightsAnalyses'][0]
    network_path_found = full_info['NetworkPathFound']
    return {
        "status" : status,
        "network_path_found" : network_path_found,
        "info" : full_info
    } 



def get_inputs():
    region = input("Please enter the AWS Region: ")
    access_key = input("Please enter the AWS Access Key: ")
    secret_key = input("Please enter the AWS Secrete Key: ")
    subnet1 = input("Please enter the source Subnet ID - Subnet1: ") 
    subnet2 = input("Please enter the destination Subnet ID - Subnet2: ") 
    # analyze_bi_direction = input("Analizy bi-direction (y/n):")
    analyze_specific_ports = input("Analizy specific ports (list comma delimited): ")
    default_ports = "22,8080,8443,3030,27117"
    if analyze_specific_ports == '':
        analyze_specific_ports = default_ports

    analyze_specific_ports_list = list(analyze_specific_ports.split(","))

    return {
        "subnet1" : subnet1,
        "subnet2" : subnet2,
        "analyze_bi_direction" : False,
        "analyze_specific_ports_list" : analyze_specific_ports_list,
        "region" : region,
        "access_key" : access_key,
        "secret_key" : secret_key
    }


def analyze(subnet1_eni, subnet2_eni, analyze_specific_ports_list):

    prints("Start analysis network connectivity of Subnet1 via: " + subnet1_eni + " --> to Subnet2 via " + subnet2_eni + ", on ports: " + str(analyze_specific_ports_list))

    analysis_result = {
        "full_network_path_found" : True,
        "path_info" : []  
    }
    
    for port in analyze_specific_ports_list:
        analyze_per_port(subnet1_eni, subnet2_eni, analysis_result, port)
    return analysis_result

def analyze_per_port(subnet1_eni, subnet2_eni, analysis_result, port):
    port = int(port)
    prints("Analyzing port: " + str(port))

    create_network_insights_path_response = create_network_insights_path(subnet1_eni, subnet2_eni, port)
    start_network_insights_analysis_resposne = start_network_insights_analysis(create_network_insights_path_response["NetworkInsightsPathId"])
    fetch_network_insights_analyses_result_response = fetch_network_insights_analyses_result(start_network_insights_analysis_resposne["NetworkInsightsAnalysisId"])
    
    if analysis_result["full_network_path_found"] != False:
        analysis_result["full_network_path_found"] = fetch_network_insights_analyses_result_response["network_path_found"]

    path_result = {
            "network_path_found" : fetch_network_insights_analyses_result_response["network_path_found"],
            "source": subnet1_eni,
            "destination": subnet2_eni,
            "port": port,
            "info": fetch_network_insights_analyses_result_response["info"],
            "insights_path_id" : create_network_insights_path_response["NetworkInsightsPathId"],
            "insights_analysis_id" : start_network_insights_analysis_resposne["NetworkInsightsAnalysisId"]
        }
    analysis_result["path_info"].append(path_result)
    print_header2("Analysis on port: " + str(port) + " completed")

def create_eni(subnetId):
    prints("Creating eni in Subnet: " + subnetId)
    response = client.create_network_interface(
        Description='eDSF Sonar Network Analyzer Tool - ' + subnetId,
        SubnetId = subnetId, 
        TagSpecifications=[
            {
                'ResourceType': 'network-interface',
                'Tags': [
                    {
                        'Key': 'project',
                        'Value': 'dsf'
                    }
                ]
            }])
    eniId = response["NetworkInterface"]["NetworkInterfaceId"]
    prints("eni created: " + eniId)
    return eniId

def delete_eni(eni_id):
    prints("Deleting eni: " + eni_id)
    response = client.delete_network_interface(NetworkInterfaceId=eni_id)

def create_network_endpoints(subnet1,subnet2):
    prints("Start creating Networking Endpoints")
    subnet1_eni = create_eni(subnet1)
    subnet2_eni = create_eni(subnet2)
    return {
        "subnet1_eni" : subnet1_eni,
        "subnet2_eni" : subnet2_eni
    }
def delete_network_endpoints(eni1_id,eni2_id):
    prints("Start deleting Networking Endpoints")
    delete_eni(eni1_id)
    delete_eni(eni2_id)

def print_header1(text):
    print("")
    print('*********************************************************')
    print('************ ' + text + " ")
    print('*********************************************************')
    print("")
    print("")

def print_header2(text):
    print("")
    print('************ ' + text)
    print("")

def prints(text):
    print(text)


def write_to_disk(analysis_result):
    file_name=str(int(time.time())) + ".txt"
    text_file = open(file_name, "w")
    n = text_file.write(json.dumps(analysis_result, indent=4, sort_keys=True, default=str))
    text_file.close()

    prints("Full info printed in file: " + file_name)

def print_links_to_console(region, analysis_result):
    prints("Full info analysis can be found in AWS Console:")
    for path_info in analysis_result["path_info"]:
        prints("   - For '" +  path_info["insights_path_id"] + "' https://" + region + ".console.aws.amazon.com/vpc/home?region=" + region + "#NetworkPath:pathId=" + path_info["insights_path_id"])

if __name__ == '__main__':
    print_header1("eDSF Sonar Network Analyzer Tool")
    inputs = get_inputs()
    client = init_client(inputs["access_key"], inputs["secret_key"], inputs["region"])
    print_header2("Analysis Started")
    endpoints = create_network_endpoints(inputs["subnet1"],inputs["subnet2"])
    analysis_result = analyze(
        endpoints["subnet1_eni"],
        endpoints["subnet2_eni"],
        inputs["analyze_specific_ports_list"])

    delete_network_endpoints(endpoints["subnet1_eni"],endpoints["subnet2_eni"])
    print_header1("Analysis completed. Full Network Path Found: " + str(analysis_result["full_network_path_found"]))
    write_to_disk(analysis_result)
    print_links_to_console(inputs["region"], analysis_result)
