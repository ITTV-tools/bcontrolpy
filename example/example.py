import asyncio
from bcontrolpy import BControl
import argparse
import aiohttp
import json  # Add this import at the top


async def main(ip, password):
    async with aiohttp.ClientSession() as session:
        async with BControl(ip, password, session=session) as bc:
            login_response = await bc.login()
            print("Login Response:", login_response)
        
        try:
            while True:
                data = await bc.get_data()
                formatted_data = format_data(data)
                print(formatted_data)
                await asyncio.sleep(5)  # Wait for 5 seconds before the next call
        except asyncio.CancelledError:
            print("Task cancelled, closing connection.")


def format_data(data):
    # Format the JSON data with indentation for readability
    return json.dumps(data, indent=4)


# Example usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BControl data retrieval')
    parser.add_argument('--ip', required=True, help='IP address of the BControl device')
    parser.add_argument('--password', required=True, help='Password for the BControl device')
    args = parser.parse_args()
    asyncio.run(main(password=args.password, ip=args.ip))