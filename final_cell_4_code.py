# Cell 4: Process each URL using OpenAI's API

# Set up OpenAI API key
api_key = userdata.get('OpenAIAPIKeyforUSCCBKey')
client = OpenAI(api_key=api_key)

def extract_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def process_url_with_openai(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract visible text from the webpage
    visible_text = ' '.join([s for s in soup.stripped_strings])

    # Prepare the prompt for OpenAI
    prompt = f"""
    Extract parish information from the following webpage content.
    The information should include: Name, Status, Deanery, EST (Established Date),
    Street Address, City, State, Zipcode, Phone Number, and Web.
    If any information is missing, use null.
    Format the output as a valid JSON object with these exact keys:
    {{"Name": null, "Status": null, "Deanery": null, "EST": null, "Street Address": null, "City": null, "State": null, "Zipcode": null, "Phone Number": null, "Web": null}}

    Webpage content:
    {visible_text[:12000]}  # Limit text to approx 3k tokens
    """

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from unstructured text. Always return a valid JSON object."},
                {"role": "user", "content": prompt}
            ]
        )

        # Attempt to parse the JSON response
        content = response.choices[0].message.content.strip()
        # Clean potential markdown code block fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        print(f"API Response (cleaned): {content}")  # Log the cleaned API response
        extracted_data = json.loads(content)
        return extracted_data
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        print(f"Raw API Response (before cleaning attempt): {response.choices[0].message.content.strip()}")
        return None
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return None

# Process each URL
for url in urls:
    url = url[0]  # Extract URL from tuple
    if not (url.startswith('http://') or url.startswith('https://')):
        print(f"Skipping invalid URL: {url}")
        continue
    print(f"Processing URL: {url}")

    try:
        parish_data = process_url_with_openai(url)

        if parish_data is None:
            print(f"Skipping URL due to processing error: {url}")
            continue

        # Add the source URL and domain to the data
        parish_data['source_url'] = url
        parish_data['domain'] = extract_domain(url)

        # Insert data into the parishes table
        cursor.execute('''
            INSERT INTO parishes (
                Name, Status, Deanery, EST, `Street Address`, City, State, Zipcode,
                PhoneNumber, Web, source_url, domain
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            parish_data.get('Name'),
            parish_data.get('Status'),
            parish_data.get('Deanery'),
            parish_data.get('EST'),
            parish_data.get('Street Address'),
            parish_data.get('City'),
            parish_data.get('State'),
            parish_data.get('Zipcode'),
            parish_data.get('Phone Number'),
            parish_data.get('Web'),
            parish_data['source_url'],
            parish_data['domain']
        ))

        conn.commit()
        print(f"Data inserted for: {parish_data.get('Name', 'Unknown Parish')}")
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")

print("All URLs processed.")
