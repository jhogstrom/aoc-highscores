import requests
import boto3
import os
import datetime
import lxml
import logging
from lxml import html
from boto3.dynamodb.conditions import Key

globalscores_table_name = os.environ.get("DDB_GLOBALSCORES", "scoreboard-globalscores")
globalscores_table = boto3.resource('dynamodb').Table(globalscores_table_name)
logging.basicConfig(level=logging.INFO)

COL_LISTSIZE = 'listsize'
COL_ID = 'year'
COL_DAY = 'day'
COL_RESULTS = 'results'

LIST_IS_FULL = 100 + 100

def get_file(url: str) -> str:
    """
    Download data from <url> and return the content.

    Args:
        url (str): url from where to pull the filw

    Returns:
        str: contentr of data downloaded from url
    """
    logging.info(f"Downloading {url}")
    headers = {'user-agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; .NET CLR 1.0.3705)'}
    r = requests.get(url, headers=headers)
    return r

def parse_file(data) -> dict:
    """
    Parse a html-file assumed to contain the global high-scores for AoC
    marked up in a special way.

    Args:
        data (str): Content of the global highscore list for a day of some year

    Returns:
        dict: map <star#> -> names
    """
    logging.info("Parsing html")
    res = [[], []]
    tree = lxml.html.fromstring(data)
    nodes = tree.xpath('//div[@class="leaderboard-entry"]')
    star = 2
    for n in nodes:
        pos = int(n.xpath('.//span[@class="leaderboard-position"]/text()')[0].strip()[:-1])
        # time = n.xpath('.//span[@class="leaderboard-time"]/text()')[0]
        names = n.xpath('.//text()')
        names = [_.strip() for _ in names if _.strip()]
        name = names[2]
        if "(anonymous user" in name:
            name = name.split("#")[1][:-1]
        if pos == 1:
            star -= 1

        res[star].append(name)
        # print(f"{pos:<3}: {name}")
    return res


def process_date(year: int, day: int) -> dict:
    """
    Download, parse and process the global highscores for <day> of <year>.

    Args:
        year (int): year to process
        day (int): date to process

    Returns:
        dict: a dictionary suitable for storeing in dynamodb.
    """
    logging.info(f"Examining {year}-{day}")
    url = F"https://adventofcode.com/{year}/leaderboard/day/{day}"
    response = get_file(url)
    if response.status_code == requests.codes.ok:
        res = parse_file(response.content)
        item = {
            COL_ID: year,
            COL_DAY: day,
            COL_LISTSIZE: len(res[0]) + len(res[1]),
            COL_RESULTS: res
        }
        return item
    else:
        logging.warning(f"Data not found for {year}-{day} - response {response.status_code}")
        return {}


def update_scores(table, year: int, day: int, stored_data: dict):
    """
    Update global scores for <day>/<year> if the day contains less than
    LIST_IS_FULL entries and the list is updated.

    Args:
        table (dynamo table/batch): Table where to store results.
        year (int): year to update.
        day (int): Day to update.
        stored_data (dict): map from <day> -> entries_count
    """
    if stored_data.get(day, 0) != LIST_IS_FULL:
        item = process_date(year, day)
        if item and stored_data.get(day, 0) != item[COL_LISTSIZE]:
            logging.info(f"Saving data for {year}-{day}")
            table.put_item(Item=item)


def data_for_year(year: int) -> dict:
    """
    Fetch the number of entries in global list per day for <year>.

    Args:
        year (int): Year to fetch

    Returns:
        dict: map <day> -> entries_count
    """
    logging.info(f"Getting stored data for {year}")
    response = globalscores_table.query(
        KeyConditionExpression=Key(COL_ID).eq(year),
        ProjectionExpression=f"#d, {COL_LISTSIZE}",
        ExpressionAttributeNames={"#d": "day"})

    res = {int(d[COL_DAY]):int(d[COL_LISTSIZE]) for d in response.get('Items', {})}
    return res


def refresh_day(year: int, day: int) -> None:
    """
    Update the information for <day>/<year>

    Args:
        year (int): Year to update.
        day (int): Day to update.
    """
    if 0 > day > 25:
        logging.warning(f"No point in requesting data for day {day}. Skipping.")
        return
    stored_data = data_for_year(year)
    update_scores(globalscores_table, year, day, stored_data)


def refresh_year(year: int) -> None:
    """
    Refresh data for all days for <year>.

    Args:
        year (int): Year to update.
    """
    stored_data = data_for_year(year)
    with globalscores_table.batch_writer() as batch:
        for day in [d for d in range(1, 26) if stored_data.get(d, 0) != LIST_IS_FULL]:
            update_scores(batch, year, day, stored_data)


def main(event, context):
    today = datetime.date.today()
    if today.month == 12 and today.day <= 25:
        refresh_day(today.year, today.day)

if __name__ == "__main__":
    refresh_year(2020)
    # refresh_day(2020, 28)



