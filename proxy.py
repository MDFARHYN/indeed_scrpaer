import asyncio

import botright

 


async def main():
    for i in range(5):
        botright_client = await botright.Botright()
        
         
        browser = await botright_client.new_browser(proxy='username:password:server_name:port'))
        page = await browser.new_page()

        # Continue by using the Page
        await page.goto("https://www.myip.com/", timeout=60000)
        
        await asyncio.sleep(3) 
        
        await botright_client.close()


if __name__ == "__main__":
    asyncio.run(main())