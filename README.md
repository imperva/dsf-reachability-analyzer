<div class="markdown prose w-full break-words dark:prose-invert light">
   <h1>DSF Reachability Analysis Tool</h1>
   <p>This is a tool that allows users to analyze network connectivity between two subnets in an Amazon VPC. The tool uses the AWS EC2 Network Insights feature to create a path between the source and destination subnets and analyzes the connectivity on specified ports.</p>
   <h2>Prerequisites</h2>
   <ul>
      <li>AWS Access Key and Secret Key with permissions to use EC2 Network Insights</li>
      <li>Python 3 and the boto3 library installed</li>
      <li>The source and destination subnet IDs</li>
   </ul>
   <h2>Usage</h2>
   <ol>
      <li>Install virtualenv by running the command <code>pip install virtualenv</code>.</li>
      <li>Create a virtual environment by running the command <code>virtualenv venv</code>.</li>
      <li>Activate the virtual environment by running the command <code>source venv/bin/activate</code> on Unix-based systems or <code>venv\Scripts\activate.bat</code> on Windows.</li>
      <li>To install the required dependencies, run the following command: <code>pip install -r requirements.txt</code></li>
      <li>Run the script by entering the command <code>python main.py</code> in the command prompt and answer the questions.</li>
      <li>When asked to, enter a list of ports to analyze connectivity on, comma separated (e.g. "22,8080,8443"). If left blank, the script will use a default list of ports (22,8080,8443,3030,27117) which are all the ports needed for a functional Sonar environment.</li>
   </ol>
   <p>
         **Note**: The script creates and deletes temporary Elastic Network Interfaces (ENIs) in order to perform the analysis. In case of failure, these ENIs may need to be deleted manually.
   </p>
    <h2>AWS IAM Roles</h2>
    <p>
    [See minimum Policy needed](https://github.com/imperva/dsf-reachability-analyzer/blob/master/iam_role.yml)
    </p>
    <h2>plan.json - Network Topology Definition</h2>
    <p>The plan.json file is used to define the network topology that will be analyzed by the DSF Reachability Analyzer. It contains two main sections: hub and gw, each of which defines a set of network resources
    </p>
    <p>
      Each resource in the hub and gw sections has the following fields:
    </p>
    <ul>
      <li><code>friendly_name</code>: A friendly name for the hub/gateway. This is used for identification purposes only.</li>
      <li><code>hadr_pair_id</code>: The ID of the High Availability and Disaster Recovery (HADR) pair that two DSF nodes are part of. In the case where two DSF Hubs or Agentless Gateways have the same "hadr_pair_id", the DSF Reachability Analyzer tool will verify network connectivity between them as part of its analysis.</li>
      <li><code>subnet</code>: The ID of the subnet where the DSF Hub/Agentless Gateway is deployed.</li>
      <li><code>security_group_id</code>: The ID of the security group associated with the DSF Hub/Agentless Gateway.</li>
      <li><code>region</code>: The AWS region where the DSF Hub/Agentless Gateway is deployed.</li>
      <li><code>peering_connection_id</code>: The ID of the VPC peering connection that connects the DSF Hub/Agentless Gateway to the target VPC. VPC peering is only necessary when two DSF nodes are located in different regions.</li>
      <li><code>outbound_internet</code>: An object that defines the outbound internet configuration for the DSF Hub/Agentless Gateway. This object contains the following fields:
          <ul>
            <li><code>type</code>: The type of outbound internet connection. Currently, the only valid option is "NAT_GATEWAY". Additional options may be added in future releases.</li>
            <li><code>id</code>: The ID of the NAT gateway to use for outbound traffic.</li>
          </ul>
      </li>
    </ul>
    <h2>Results</h2>
   <p>On Analysis completion the results can be viewd in 3 places:
   <ol>
      <li>On the terminal you will be able to see the basic info</li>
       <li>A file will be generated to include all the analysis including detail info</li>
       <li>On the terminal you will see direct links to AWS Network Analyzer service. The links will bring you directly to the specific analysis. Note that you need to be logged in to the correspondant AWS account</li>
   </ol>
   </p>
   <h2>Additional note</h2>
   <p>It is recommended to use environment variable to manage the aws key and secret key or better using IAM to grant access to your AWS resource, instead of hardcoding them in the script</p>
</div>
