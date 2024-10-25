import json
from html import escape, unescape
from urllib.parse import quote, unquote
import logging
import requests
from pprint import pprint
from functools import reduce
import sys
import csv
from thefuzz import fuzz

YGOPRODECK_API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
orderwand_csv_filename = sys.argv[1]

manifest = []
total_spent = 0
#total_value_min = 0
#total_value_max = 0
potential_value = 0

with open(orderwand_csv_filename, "r") as orderwand_csv:
    # read csv
    reader = csv.DictReader(orderwand_csv)
    for order in reader:
        received = True if order["Shipping Status"] != "cancelled" else False
        if not received:
            continue

        card_name = unescape(order["Product Name"])
        set_name = order["Set Name"]

        price = float(order["Price"])
        quantity = int(order["Quantity"])


        result : requests.Response = requests.get(
                YGOPRODECK_API_URL,
                params={"name": card_name, "tcgplayer_data": 1},
            )



        if result.status_code != 200:
            logging.warning("API request failed for " + card_name + ": " + result.text)
            continue

        card_info = json.loads(result.text)['data'][0]

        card_sets = [x for x in card_info["card_sets"] if fuzz.partial_ratio(x["set_name"], set_name) >= 100]
        card_sets_fuzzmap = [(x['set_name'], fuzz.partial_ratio(x["set_name"], set_name)) for x in card_info["card_sets"]]
        if len(card_sets) < 1:
            logging.warning("No sets found matching '" + set_name + "' for '" + card_name + "': " + str(card_sets_fuzzmap))
            #pprint(card_info)
            continue
        if len(card_sets) > 1:
            logging.info("Multiple sets found matching '" + set_name + "' for '" + card_name + "':" + str(card_sets_fuzzmap))
        card_set_with_cheapest = reduce(lambda a, b: a if a["set_price"] < b["set_price"] else b, [x for x in card_sets])
        #min_value, max_value = min([float(x["set_price"]) for x in card_sets]), max([float(x["set_price"]) for x in card_sets])
        #pprint(card_info)

        #total_value_min += min_value * quantity
        #total_value_max += max_value * quantity
        #print(int(total_value_min - total_spent), int(total_value_max - total_spent))

        card_order = {
            "card_name": card_name,
            "set_code": card_set_with_cheapest["set_code"],
            "lowest_current_value": float(card_set_with_cheapest["set_price"]),
            "cost_basis": price,
            "quanity": quantity,
            "order_id": order["Order Id"],
            "ordered_at": order["Ordered At"]
        }

        manifest += [card_order]
        if card_order["lowest_current_value"] > card_order["cost_basis"]:

            total_spent += price * quantity
            potential_value += card_order["lowest_current_value"] * quantity
            print(potential_value - total_spent)
            #print(card_order)

with open("cardorders.csv", "w") as f:
    writer = csv.DictWriter(f, manifest[0].keys())
    writer.writeheader()
    writer.writerows(manifest)

print("total spent:", total_spent)
print("total possible value:", potential_value)
print("total possible profit:", potential_value - total_spent)

