import sys
import boto3
from botocore.exceptions import ClientError


#Get the current status of the EventBridge rule
def get_rule_status(rule_name='FifteenMinuteSchedule'):
    try:
        events_client = boto3.client('events')
        response = events_client.describe_rule(Name=rule_name)
        return response['State']
    except ClientError as e:
        print(f"Error getting rule status: {e}")
        return None

#Enable the EventBridge simulator
def enable_simulator(rule_name='FifteenMinuteSchedule'):
    try:
        events_client = boto3.client('events')
        events_client.enable_rule(Name=rule_name)
        print(f"EventBridge simulator '{rule_name}' has been ENABLED")
        print("The simulator will now generate test events every 15 minutes")
        return True
    except ClientError as e:
        print(f" Error enabling simulator: {e}")
        return False
    
#Disable the EventBridge simulator
def disable_simulator(rule_name='FifteenMinuteSchedule'):
    try:
        events_client = boto3.client('events')
        events_client.disable_rule(Name=rule_name)
        print(f" EventBridge simulator '{rule_name}' has been DISABLED")
        print("The simulator will stop generating test events")
        return True
    except ClientError as e:
        print(f" Error disabling simulator: {e}")
        return False

#Show the current status of the simulator
def show_status(rule_name='FifteenMinuteSchedule'):
    status = get_rule_status(rule_name)
    if status:
        print(f"EventBridge Simulator Status: {status}")
        if status == 'ENABLED':
            print("The simulator is currently generating test events every 15 minutes")
        else:
            print("The simulator is currently disabled")
    else:
        print(f"Could not retrieve status for rule '{rule_name}'")

#Show help information
def show_help():
    print("EventBridge Simulator Control")
    print("=" * 30)
    print("Usage:")
    print("python simulator_control.py enable ")
    print("python simulator_control.py disable ")
    print("python simulator_control.py status ")
    print("python simulator_control.py help ")
    print()
    print("The simulator generates vehicle location data every 15 minutes")
    print("and sends it to the LocationStream Kinesis stream.")

def main():
    if len(sys.argv) != 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'enable':
        enable_simulator()
    elif command == 'disable':
        disable_simulator()
    elif command == 'status':
        show_status()
    elif command == 'help':
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()