from openai import OpenAI
import os

base_url = os.environ.get("BASE_URL")
model = os.environ.get("MODEL")
api_key = os.getenv('OPENROUTER_API_KEY')

def chat_with_ai(user_input):

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    # Personality
    conversation = [
        {
            "role": "system",
            "content": """You are helpinh me to find a house and it has to be for 2 people, so 2 rooms at least for up to 750 euros per person,
            if the price is higher than that, you should consider if adding another person would be ok, in this case the price should be up to 700 euros per person, so 3 rooms in this case.
            In your reply True or False,so i understand if the house is ok or not, then explain why.
            """,
        },
    ]
    conversation.append({"role": "user", "content": user_input})
    stream = client.chat.completions.create(
        model=model,
        messages=conversation,
        stream=True
    )
    first_chunk = next(iter(stream), None)
    if first_chunk:
        first_message = first_chunk.choices[0].delta.content or ""
        print("First sentence:", first_message.split('.')[0] + ".")
    for chunk in stream:
        chunk_message = chunk.choices[0].delta.content or ""
        print(chunk_message, end="")

    # print("chunk_message", stream)
   

if __name__ == "__main__":
    user_input = """
    Description
    Een prachtig licht 4-kamer (3 slaapkamer) appartement in het centrum van Rotterdam.
    Wonen aan de Hoogstraat 20-D betekent genieten van het ultieme stadsleven. Dit appartement ligt midden in de bruisende Stadsdriehoek, op loopafstand van de Markthal, de Meent en de sfeervolle Oude Haven. Trendy winkels, hippe koffiebars en toprestaurants liggen letterlijk om de hoek.
    De bereikbaarheid is perfect: Station Blaak, tram- en busverbindingen en fietsroutes brengen je in no-time door de hele stad. Tegelijkertijd bieden de Maas en nabijgelegen parken de nodige rust en ontspanning.
    Layout:
    Entree appartement op 4e verdieping in hal van waaruit alle kamers bereikbaar zijn.
    De ruime en lichte woonkamer heeft een Frans balkon. Er is hier voldoende ruimte voor een eettafel met stoelen en een grote hoekbank met televisie.
    Vanuit de hal heb je toegang tot de keuken. Deze is voorzien van inbouwapparatuur zoals gasfornuis, afzuigkap, vaatwasser, koelkast en vriezer.
    De hoofdslaapkamer heeft veel natuurlijk licht door de grote ramen. Deze is ruim en hier past een tweepersoonsbed en een kledingkast.
    De tweede slaapkamer bevindt zich naast de woonkamer en deze kamer is zeer geschikt als kinderkamer of een logeerkamer.
    De derde slaapkamer is iets kleiner van formaat, maar is goed om te gebruiken als kledingkast of kantoor aan huis
    De badkamer heeft een inloopdouche en een wastafel met bergruimte eronder en een spiegel.
    Vanuit de hal bereik je het separate toilet en de berging met de wasmachineaansluiting.
    Opmerkingen:
    De huur is exclusief nutsvoorzieningen;
    Nutsvoorzieningen zijn € 250,00 voorschot per maand
    Minimale huurperiode 12 maanden;
    Externe opslag.
    *** English
    A beautiful bright 4-room (3 bedroom) apartment in the center of Rotterdam.
    Living at Hoogstraat 20-D means enjoying the ultimate city life. This apartment is located in the middle of the bustling Stadsdriehoek, within walking distance of the Markthal, the Meent and the attractive Oude Haven. Trendy stores, hip coffee bars and top restaurants are literally around the corner.
    Accessibility is perfect: Blaak Station, streetcar and bus connections and bicycle routes take you throughout the city in no time. At the same time, the Maas River and nearby parks offer the necessary rest and relaxation.
    Layout:
    Entrance apartment on 4th floor in hall from where all rooms are accessible.
    The spacious and bright living room has a French balcony. There is enough space here for a dining table with chairs and a large corner sofa with television.
    From the hall you have access to the kitchen. This is equipped with built-in appliances such as gas stove, extractor hood, dishwasher, refrigerator and freezer.
    The master bedroom has plenty of natural light through the large windows. This is spacious and here fits a double bed and a closet.
    The second bedroom is next to the living room and this room is very suitable as a children's room or a guest room.
    The third bedroom is slightly smaller in size, but is good to use as a closet or home office
    The bathroom has a walk-in shower and a sink with storage space underneath and a mirror.
    From the hall you reach the separate toilet and the storage room with the washing machine connection.
    Comments:
    The rent is excluding utilities;
    utilities are € 250,00 advanced payment per month
    Minimum period of 12 months;
    External storage.
        €1,995 per month
    """
    chat_with_ai(user_input)