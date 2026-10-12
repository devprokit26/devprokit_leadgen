"""places.py - mulk -> shehar -> towns. Naya shehar/town yahan add kar sakte ho (comma se alag)."""

def _t(s):
    return [x.strip() for x in s.split(",") if x.strip()]

CANADA_CITIES = _t("""Toronto, Montreal, Vancouver, Calgary, Edmonton, Ottawa, Winnipeg, Quebec City, Hamilton, Kitchener, London,
Victoria, Halifax, Oshawa, Windsor, Saskatoon, Regina, St. Catharines, Barrie, Kelowna, Abbotsford, Kingston, Sherbrooke,
Guelph, Moncton, Saguenay, Trois-Rivieres, Brantford, Thunder Bay, Saint John, Peterborough, Sudbury, Lethbridge, Nanaimo,
Kamloops, Red Deer, Fredericton, Chilliwack, Cambridge, Waterloo, Niagara Falls, Belleville, Sarnia, Sault Ste. Marie,
North Bay, Cornwall, Welland, Timmins, Woodstock, Stratford, Orillia, Cobourg, Brockville, Chatham-Kent, Mississauga,
Brampton, Markham, Vaughan, Richmond Hill, Oakville, Burlington, Whitby, Ajax, Pickering, Newmarket, Aurora, Milton,
Laval, Gatineau, Longueuil, Levis, Terrebonne, Repentigny, Drummondville, Granby, Saint-Jerome, Brossard, Shawinigan,
Rimouski, Victoriaville, Rouyn-Noranda, Saint-Hyacinthe, Saint-Jean-sur-Richelieu, Surrey, Burnaby, Richmond, Coquitlam,
Langley, Saanich, Delta, Prince George, Vernon, Maple Ridge, Penticton, Courtenay, Campbell River, Fort St. John, Cranbrook,
Calgary North, St. Albert, Medicine Hat, Grande Prairie, Airdrie, Spruce Grove, Fort McMurray, Leduc, Okotoks, Cochrane,
Lloydminster, Camrose, Brooks, Brandon, Steinbach, Prince Albert, Moose Jaw, Swift Current, Yorkton, North Battleford,
Dartmouth, Sydney, Truro, Miramichi, Charlottetown, Summerside, St. John's, Corner Brook, Mount Pearl, Gander,
Whitehorse, Yellowknife, Iqaluit""")
CANADA_CITIES.remove("Calgary North")

CANADA_TOWNS = {
 "Toronto": _t("Etobicoke, Scarborough, North York, East York, York, Woodbridge"),
 "Ottawa": _t("Kanata, Orleans, Nepean, Barrhaven, Stittsville, Manotick"),
 "Montreal": _t("Lachine, Verdun, Anjou, Pointe-Claire, Dorval, Saint-Laurent, Westmount, LaSalle"),
 "Vancouver": _t("North Vancouver, West Vancouver, New Westminster, Port Moody, Port Coquitlam, White Rock"),
 "Calgary": _t("Airdrie, Cochrane, Chestermere, Okotoks, Strathmore, High River"),
 "Edmonton": _t("Sherwood Park, Stony Plain, Fort Saskatchewan, Beaumont, Devon"),
 "Winnipeg": _t("Selkirk, Stonewall, Niverville, Headingley"),
 "Hamilton": _t("Ancaster, Dundas, Stoney Creek, Waterdown, Grimsby"),
 "Mississauga": _t("Streetsville, Port Credit, Malton, Meadowvale"),
 "Brampton": _t("Bolton, Caledon, Georgetown"),
 "London": _t("St. Thomas, Strathroy, Ingersoll"),
 "Kitchener": _t("Elmira, New Hamburg, Breslau"),
 "Halifax": _t("Bedford, Lower Sackville, Cole Harbour"),
 "Quebec City": _t("Beauport, Charlesbourg, Sainte-Foy, L'Ancienne-Lorette"),
 "Surrey": _t("Cloverdale, Guildford, Newton, Fleetwood"),
 "Victoria": _t("Sidney, Colwood, Langford, Sooke"),
 "Saskatoon": _t("Warman, Martensville, Osler"),
 "Regina": _t("Pilot Butte, White City, Balgonie"),
 "Windsor": _t("Tecumseh, Amherstburg, Lakeshore"),
 "Oshawa": _t("Bowmanville, Courtice, Clarington"),
 "Barrie": _t("Innisfil, Midhurst, Angus"),
 "Kelowna": _t("West Kelowna, Lake Country, Peachland"),
 "Kingston": _t("Napanee, Gananoque"),
 "Laval": _t("Sainte-Rose, Chomedey, Vimont"),
 "Gatineau": _t("Aylmer, Hull, Buckingham"),
 "Markham": _t("Unionville, Stouffville, Thornhill"),
 "Vaughan": _t("Maple, Kleinburg, Concord"),
 "Moncton": _t("Dieppe, Riverview"),
 "Saint John": _t("Rothesay, Quispamsis"),
 "St. John's": _t("Paradise, Conception Bay South"),
 "Sudbury": _t("Lively, Azilda"),
}

GERMANY_CITIES = _t("""Berlin, Hamburg, Muenchen, Koeln, Frankfurt, Stuttgart, Duesseldorf, Leipzig, Dortmund, Essen, Bremen, Dresden,
Hannover, Nuernberg, Duisburg, Bochum, Wuppertal, Bielefeld, Bonn, Muenster, Mannheim, Karlsruhe, Augsburg, Wiesbaden,
Moenchengladbach, Gelsenkirchen, Braunschweig, Aachen, Kiel, Chemnitz, Halle, Magdeburg, Freiburg, Krefeld, Luebeck,
Oberhausen, Erfurt, Mainz, Rostock, Kassel, Hagen, Hamm, Saarbruecken, Muelheim an der Ruhr, Potsdam, Ludwigshafen,
Oldenburg, Leverkusen, Osnabrueck, Solingen, Heidelberg, Herne, Neuss, Darmstadt, Paderborn, Regensburg, Ingolstadt,
Wuerzburg, Wolfsburg, Fuerth, Ulm, Heilbronn, Pforzheim, Goettingen, Bottrop, Trier, Recklinghausen, Reutlingen,
Bremerhaven, Koblenz, Bergisch Gladbach, Jena, Remscheid, Erlangen, Moers, Siegen, Hildesheim, Salzgitter, Cottbus, Gera,
Kaiserslautern, Guetersloh, Witten, Iserlohn, Schwerin, Zwickau, Dessau, Flensburg, Konstanz, Giessen, Luedenscheid,
Neubrandenburg, Offenbach, Bamberg, Bayreuth, Plauen, Passau, Rosenheim, Landshut, Kempten, Villingen-Schwenningen,
Baden-Baden, Celle, Lueneburg, Stralsund, Greifswald, Wismar, Fulda, Marburg, Worms, Speyer, Neumuenster, Norderstedt""")

GERMANY_TOWNS = {
 "Hamburg": _t("Wandsbek, Altona, Harburg, Bergedorf, Pinneberg, Ahrensburg"),
 "Berlin": _t("Spandau, Charlottenburg, Neukoelln, Pankow, Schoenefeld, Hennigsdorf"),
 "Muenchen": _t("Garching, Unterschleissheim, Ismaning, Planegg, Freising, Dachau"),
 "Koeln": _t("Frechen, Pulheim, Huerth, Troisdorf, Bergheim"),
 "Frankfurt": _t("Eschborn, Neu-Isenburg, Bad Homburg, Hanau, Ruesselsheim"),
 "Stuttgart": _t("Esslingen, Ludwigsburg, Sindelfingen, Boeblingen, Fellbach"),
 "Duesseldorf": _t("Ratingen, Meerbusch, Hilden, Langenfeld, Erkrath"),
 "Dortmund": _t("Unna, Luenen, Schwerte, Castrop-Rauxel"),
 "Essen": _t("Velbert, Heiligenhaus, Gladbeck"),
 "Leipzig": _t("Markkleeberg, Schkeuditz, Taucha, Borna"),
 "Nuernberg": _t("Schwabach, Stein, Lauf, Zirndorf"),
 "Hannover": _t("Langenhagen, Laatzen, Garbsen, Lehrte, Seelze"),
 "Bremen": _t("Delmenhorst, Stuhr, Weyhe, Achim"),
 "Dresden": _t("Radebeul, Freital, Pirna, Heidenau"),
 "Mannheim": _t("Viernheim, Weinheim, Schwetzingen"),
 "Karlsruhe": _t("Ettlingen, Rastatt, Bruchsal"),
 "Augsburg": _t("Friedberg, Neusaess, Gersthofen"),
 "Bielefeld": _t("Herford, Werther, Halle (Westf.)"),
 "Bonn": _t("Siegburg, Troisdorf, Meckenheim, Bad Godesberg"),
 "Muenster": _t("Telgte, Greven, Ahlen"),
}

PAKISTAN_CITIES = _t("""Karachi, Lahore, Faisalabad, Rawalpindi, Gujranwala, Peshawar, Multan, Hyderabad, Islamabad, Quetta, Bahawalpur,
Sargodha, Sialkot, Sukkur, Larkana, Sheikhupura, Rahim Yar Khan, Jhang, Dera Ghazi Khan, Gujrat, Sahiwal, Wah Cantonment,
Mardan, Kasur, Okara, Mingora, Nawabshah, Chiniot, Kotri, Kamoke, Hafizabad, Sadiqabad, Mirpur Khas, Burewala, Kohat,
Khanewal, Dera Ismail Khan, Turbat, Muzaffargarh, Abbottabad, Mandi Bahauddin, Shikarpur, Jacobabad, Jhelum, Khanpur,
Khairpur, Khuzdar, Pakpattan, Hub, Daska, Gojra, Muridke, Bahawalnagar, Samundri, Tando Allahyar, Tando Adam, Jaranwala,
Chishtian, Muzaffarabad, Attock, Vehari, Chakwal, Kamalia, Umerkot, Ahmedpur East, Kot Addu, Wazirabad, Mansehra, Swabi,
Nowshera, Charsadda, Bannu, Gwadar, Lodhran, Layyah, Toba Tek Singh, Narowal, Mianwali, Bhakkar, Sambrial, Pasrur""")
PAKISTAN_TOWNS = {
 "Sialkot": _t("Daska, Sambrial, Pasrur, Ugoke, Begowala, Kotli Loharan, Chawinda, Bajwat, Sialkot Cantt"),
 "Lahore": _t("Raiwind, Model Town, Gulberg, Johar Town, Shahdara, Wagah, Bedian, Defence"),
 "Karachi": _t("Korangi, Landhi, North Karachi, SITE, Gulshan-e-Iqbal, Clifton, Bin Qasim, Saddar"),
 "Faisalabad": _t("Jaranwala, Samundri, Tandlianwala, Chak Jhumra, Sammundri"),
 "Rawalpindi": _t("Taxila, Gujar Khan, Kahuta, Murree, Saddar"),
 "Islamabad": _t("Bhara Kahu, Tarnol, I-9 Industrial Area, Rawat, Golra"),
 "Gujranwala": _t("Wazirabad, Kamoke, Nowshera Virkan, Aimanabad, Eminabad, Gujranwala Cantt"),
 "Peshawar": _t("Hayatabad, Badaber, Warsak, Pabbi"),
 "Multan": _t("Shujabad, Jalalpur Pirwala, Mailsi, Multan Cantt"),
 "Hyderabad": _t("Latifabad, Qasimabad, Tando Jam, Hala"),
 "Sheikhupura": _t("Muridke, Ferozwala, Farooqabad, Sharaqpur"),
 "Gujrat": _t("Kharian, Jalalpur Jattan, Sarai Alamgir, Lalamusa"),
 "Sargodha": _t("Bhalwal, Shahpur, Sillanwali"),
 "Quetta": _t("Hanna, Pishin, Kuchlak"),
 "Bahawalpur": _t("Hasilpur, Yazman, Khairpur Tamewali"),
}

COUNTRIES = {
 "Canada": (CANADA_CITIES, CANADA_TOWNS),
 "Germany": (GERMANY_CITIES, GERMANY_TOWNS),
 "United States": (_t("New York, Los Angeles, Chicago, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Dallas, San Jose, Austin, Jacksonville, Fort Worth, Columbus, Charlotte, Indianapolis, San Francisco, Seattle, Denver, Washington, Boston, Nashville, Detroit, Portland, Las Vegas, Memphis, Atlanta, Miami, Minneapolis, Cleveland"), {}),
 "United Kingdom": (_t("London, Birmingham, Manchester, Glasgow, Liverpool, Leeds, Sheffield, Edinburgh, Bristol, Cardiff, Leicester, Nottingham, Newcastle, Belfast, Southampton, Coventry, Bradford"), {}),
 "France": (_t("Paris, Marseille, Lyon, Toulouse, Nice, Nantes, Strasbourg, Montpellier, Bordeaux, Lille, Rennes"), {}),
 "Italy": (_t("Roma, Milano, Napoli, Torino, Palermo, Genova, Bologna, Firenze, Bari, Verona"), {}),
 "Spain": (_t("Madrid, Barcelona, Valencia, Sevilla, Zaragoza, Malaga, Bilbao"), {}),
 "Netherlands": (_t("Amsterdam, Rotterdam, Den Haag, Utrecht, Eindhoven, Groningen"), {}),
 "United Arab Emirates": (_t("Dubai, Abu Dhabi, Sharjah, Ajman"), {}),
 "Pakistan": (PAKISTAN_CITIES, PAKISTAN_TOWNS),
 "Australia": (_t("Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra"), {}),
}

def as_json():
    return {c: {"cities": ci, "towns": to} for c, (ci, to) in COUNTRIES.items()}


ALL_COUNTRIES = _t("""Afghanistan, Albania, Algeria, Andorra, Angola, Argentina, Armenia, Australia, Austria, Azerbaijan, Bahamas, Bahrain,
Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bhutan, Bolivia, Bosnia and Herzegovina, Botswana, Brazil, Brunei,
Bulgaria, Burkina Faso, Burundi, Cambodia, Cameroon, Canada, Chad, Chile, China, Colombia, Congo, Costa Rica, Croatia, Cuba,
Cyprus, Czech Republic, Denmark, Djibouti, Dominican Republic, Ecuador, Egypt, El Salvador, Estonia, Ethiopia, Fiji, Finland,
France, Gabon, Gambia, Georgia, Germany, Ghana, Greece, Guatemala, Guinea, Guyana, Haiti, Honduras, Hong Kong, Hungary,
Iceland, India, Indonesia, Iran, Iraq, Ireland, Israel, Italy, Ivory Coast, Jamaica, Japan, Jordan, Kazakhstan, Kenya,
Kuwait, Kyrgyzstan, Laos, Latvia, Lebanon, Liberia, Libya, Lithuania, Luxembourg, Macedonia, Madagascar, Malawi, Malaysia,
Maldives, Mali, Malta, Mauritius, Mexico, Moldova, Monaco, Mongolia, Montenegro, Morocco, Mozambique, Myanmar, Namibia,
Nepal, Netherlands, New Zealand, Nicaragua, Niger, Nigeria, Norway, Oman, Pakistan, Palestine, Panama, Papua New Guinea,
Paraguay, Peru, Philippines, Poland, Portugal, Qatar, Romania, Russia, Rwanda, Saudi Arabia, Senegal, Serbia, Singapore,
Slovakia, Slovenia, Somalia, South Africa, South Korea, South Sudan, Spain, Sri Lanka, Sudan, Suriname, Sweden, Switzerland,
Syria, Taiwan, Tajikistan, Tanzania, Thailand, Togo, Trinidad and Tobago, Tunisia, Turkey, Turkmenistan, Uganda, Ukraine,
United Arab Emirates, United Kingdom, United States, Uruguay, Uzbekistan, Venezuela, Vietnam, Yemen, Zambia, Zimbabwe""")