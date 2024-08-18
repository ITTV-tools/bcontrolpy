# bcontrolpy
This module lets you read the data from a BControl EM300.

Example:
```python
import asyncio
import bcontrolpy
# Exmaple usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BControl data retrieval')
    parser.add_argument('--ip', required=True, help='IP address of the BControl device')
    parser.add_argument('--password', required=True, help='Password for the BControl device')
    args = parser.parse_args()
    async def main():
        bcontrol = BControl(args.ip, args.password)
        await bcontrol.login()
        data = await bcontrol.get_data()
        print(data)
        await bcontrol.close()

    asyncio.run(main())
```
