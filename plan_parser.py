def validate_plan(data):
    # Validate hub and gw lists
    for entity_type in ['hub', 'gw']:
        for entity in data.get(entity_type, []):
            # Ensure entity has a friendly_name attribute
            if 'friendly_name' not in entity:
                handleError(f'Missing friendly_name attribute in {entity_type} entity')

            # Ensure entity has a subnet attribute
            if 'subnet' not in entity:
                handleError(f'Missing subnet attribute in {entity_type} entity')

            # Ensure entity has a security_group_id attribute
            if 'security_group_id' not in entity:
                handleError(f'Missing security_group_id attribute in {entity_type} entity')

            # Ensure entity has a region attribute
            if 'region' not in entity:
                handleError(f'Missing region attribute in {entity_type} entity')

            # Ensure the subnet attribute is a valid subnet ID
            if not entity['subnet'].startswith('subnet-'):
                handleError(f'Invalid subnet ID {entity["subnet"]} in {entity_type} entity')

            # Ensure the security_group_id attribute is a valid security group ID
            if not entity['security_group_id'].startswith('sg-'):
                handleError(f'Invalid security group ID {entity["security_group_id"]} in {entity_type} entity')

            # Validate optional attributes
            if 'outbound_internet' in entity:
                outbound_internet = entity['outbound_internet']
                if not isinstance(outbound_internet, dict):
                    handleError(f'outbound_internet attribute in {entity_type} entity must be a dictionary')
                if 'type' not in outbound_internet or 'id' not in outbound_internet:
                    handleError(f'Missing required attributes in outbound_internet for {entity_type} entity')
                if outbound_internet['type'] not in ['NAT_GATEWAY', 'INTERNET_GATEWAY']:
                    handleError(f'Invalid outbound_internet type {outbound_internet["type"]} for {entity_type} entity')
                if not outbound_internet['id'].startswith('nat-') and not outbound_internet['id'].startswith('igw-'):
                    handleError(f'Invalid outbound_internet ID {outbound_internet["id"]} for {entity_type} entity')

            if 'peering_connection_id' in entity:
                peering_connection_id = entity['peering_connection_id']
                if not peering_connection_id.startswith('pcx-'):
                    handleError(f'Invalid peering_connection_id {peering_connection_id} in {entity_type} entity')

def handleError(msg):
    print(msg)
    exit(1)

def parse_plan(data):
    # Create empty list and set to store the combinations
    combinations = []
    combination_set = set()
    regions_set = set()

    # Iterate over the hub list
    for hub in data["hub"]:
        # Iterate over the hub list again to find other hubs with the same hadr_pair_id
        for other_hub in data["hub"]:
            if "hadr_pair_id" in hub and "hadr_pair_id" in other_hub and hub["hadr_pair_id"] == other_hub["hadr_pair_id"] and hub["friendly_name"] != other_hub["friendly_name"]:
                subnet_tuple = (hub["subnet"], other_hub["subnet"])
                subnet_tuple2 = (other_hub["subnet"], hub["subnet"])

                if subnet_tuple not in combination_set and subnet_tuple2 not in combination_set:
                    combination_set.add(subnet_tuple)
                    combination_set.add(subnet_tuple2)
                
                    combinations.append({"source": hub, "destination": other_hub})
                    combinations.append({"source": other_hub, "destination": hub})
                    
        # Iterate over the gws list
        for gw in data["gw"]:
            subnet_tuple = (hub["subnet"], gw["subnet"])
            if subnet_tuple not in combination_set:
                # Add the combination to the set
                combination_set.add(subnet_tuple)
                # Add the combination of subnets to the list, with the hub as "source" and gw as "destination"
                combinations.append({"source": hub, "destination": gw})

        if "outbound_internet" in hub:
            subnet_tuple = (hub["subnet"], hub["outbound_internet"]["id"])
            if subnet_tuple not in combination_set:
                combination_set.add(subnet_tuple)
                combinations.append({"source": hub, "destination": hub["outbound_internet"]})

        if "region" in hub and hub["region"] not in regions_set:
            regions_set.add(hub["region"])
                
    for gw in data["gw"]:
        for other_gw in data["gw"]:
            if "hadr_pair_id" in gw and "hadr_pair_id" in other_gw and gw["hadr_pair_id"] == other_gw["hadr_pair_id"] and gw["friendly_name"] != other_gw["friendly_name"]:
                subnet_tuple = (gw["subnet"], other_gw["subnet"])
                subnet_tuple2 = (other_gw["subnet"], gw["subnet"])
                if subnet_tuple not in combination_set and subnet_tuple2 not in combination_set:
                    combination_set.add(subnet_tuple)
                    combination_set.add(subnet_tuple2)
                    combinations.append({"source": gw, "destination": other_gw})
                    combinations.append({"source": other_gw, "destination": gw})
            
        if "outbound_internet" in gw:
            subnet_tuple = (gw["subnet"], gw["outbound_internet"]["id"])
            if subnet_tuple not in combination_set:
                combination_set.add(subnet_tuple)
                combinations.append({"source": gw, "destination": gw["outbound_internet"]})

        if "region" in gw and gw["region"] not in regions_set:
            regions_set.add(gw["region"])

    return {"plan": combinations, "regions": regions_set}