<div class="markdown prose w-full break-words dark:prose-invert light">
   <h1>Network Connectivity Analysis Tool</h1>
   <p>This is a tool that allows users to analyze network connectivity between two subnets in an Amazon VPC. The tool uses the AWS EC2 Network Insights feature to create a path between the source and destination subnets and analyzes the connectivity on specified ports.</p>
   <h2>Prerequisites</h2>
   <ul>
      <li>AWS Access Key and Secret Key with permissions to use EC2 Network Insights</li>
      <li>Python 3 and the boto3 library installed</li>
      <li>The source and destination subnet IDs</li>
   </ul>
   <h2>Usage</h2>
   <ol>
      <li>Run the script by entering the command <code>python main.py</code> in the command prompt.</li>
      <li>When asked to, enter a list of ports to analyze connectivity on, comma separated (e.g. "22,8080,8443"). If left blank, the script will use a default list of ports (22,8080,8443,3030,27117).</li>
      **Note**: The script creates and deletes temporary Elastic Network Interfaces (ENIs) in order to perform the analysis. In case of failure, these ENIs may need to be deleted manually.
   </ol>
   <h2>Functions</h2>
   <h3><code>init_client(region)</code></h3>
   <ul>
      <li>Creates a session with the specified AWS access key and secret key and returns an EC2 client.</li>
   </ul>
   <h3><code>create_network_insights_path(source, destination,port)</code></h3>
   <ul>
      <li>Creates a network insights path between the source and destination subnets, on the specified protocol and port. Returns the NetworkInsightsPathId.</li>
   </ul>
   <h3><code>start_network_insights_analysis(network_insights_path_id)</code></h3>
   <ul>
      <li>Starts the network insights analysis on the path specified by network_insights_path_id. Returns the NetworkInsightsAnalysisId.</li>
   </ul>
   <h3><code>fetch_network_insights_analyses_result(analysis_id)</code></h3>
   <ul>
      <li>Fetches the results of the network insights analysis and returns the status and whether a path was found.</li>
   </ul>
   <h3><code>get_inputs()</code></h3>
   <ul>
      <li>Prompts the user for the region, source and destination subnet IDs, and ports to analyze connectivity on.</li>
   </ul>
   <h3><code>analyze(subnet1_eni, subnet2_eni, analyze_specific_ports_list)</code></h3>
   <ul>
      <li>Function that performs the analysis on specified ports and prints out the result.</li>
   </ul>
   <h2>Additional note</h2>
   <p>It is recommended to use environment variable to manage the aws key and secret key or better using IAM to grant access to your AWS resource, instead of hardcoding them in the script</p>
</div>
