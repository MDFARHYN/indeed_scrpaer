import asyncio
import botright

async def main():
    botright_client = await botright.Botright()
    browser = await botright_client.new_browser()
    page = await browser.new_page()

    # Visit a page with reCAPTCHA
    await page.goto("https://www.google.com/recaptcha/api2/demo", timeout=60000)

    # Solve the reCAPTCHA
    await page.solve_recaptcha()

    # Wait for some time to ensure reCAPTCHA is solved
    await asyncio.sleep(2)

    # Retrieve the CAPTCHA response token from the hidden input field
    captcha_response = await page.evaluate('''() => {
        const responseField = document.querySelector('textarea[name="g-recaptcha-response"]');
        return responseField ? responseField.value : null;
    }''')

    print("CAPTCHA Response Token:", captcha_response)

    # Attempt to click the reCAPTCHA submit button
    submit_button = await page.query_selector('#recaptcha-demo-submit')
    if submit_button:
        await submit_button.click()

    
    await asyncio.sleep(3)
    await botright_client.close()


if __name__ == "__main__":
    asyncio.run(main())
