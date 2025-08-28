def fetch_satellite_image(lat, lon, name):
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lon}&zoom=18&size=640x640&maptype=satellite&key={API_KEY}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return None

    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    draw = ImageDraw.Draw(image)

    font_size = 24
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    label = name.replace("_", " ")

    # Use getbbox for text size
    try:
        bbox = font.getbbox(label)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = draw.textlength(label, font=font), font_size

    x = (image.width - text_width) // 2
    y = image.height - text_height - 10

    draw.text((x, y), label, fill="white", font=font)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.read()
