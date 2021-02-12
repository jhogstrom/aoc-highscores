import datetime
import logging
import scores
import logging


def astime(n: int) -> str:
    if n is None:
        return "n/a"
    SECSINMIN = 60
    SECSINHOUR = SECSINMIN * 60
    HOURSINDAY = 24
    SECSINDAY = HOURSINDAY * SECSINHOUR
    d = n // SECSINDAY
    n %= SECSINDAY
    h = n // SECSINHOUR
    n %= SECSINHOUR
    m = n // SECSINMIN
    n %= SECSINMIN
    if d > 0:
        return f"{d:02}.{h:02}:{m:02}:{n:02}"
    return f"{h:02}:{m:02}:{n:02}"



class BaseObj():
    pass


class Star(BaseObj):
    def __init__(self, score: dict):
        # print(f"Star: {score}")
        self.completiontime = score.get('get_star_ts', None)
        self.completiontime = int(self.completiontime) if self.completiontime else None

        self.position = None
        self.accumulatedscore = 0
        self.accumulatedtobiiscore = 0
        self.accumulatedposition = None
        self.globalscore = 0
        self.timetocomplete: int = None
        self.accumulatedtimetocomplete: int = None
        self.offsetfromwinner = None

    @property
    def starcount(self) -> int:
        return int(self.completed)

    @property
    def completed(self) -> bool:
        return self.completiontime is not None

    def __str__(self):
        return f"{self.completiontime}"


class PlayerDay(BaseObj):
    def __init__(self, score: dict):
        # print(f"Playerday: {str(score)}\n\n")
        self.stars = [Star(score.get('1', {})), Star(score.get('2', {}))]
        self.star2pos = 0
        if self.starcount == 2:
            self.timetocompletestar2 = self[1].completiontime - self[0].completiontime
        else:
            self.timetocompletestar2 = None

    def __str__(self):
        return " - ".join([str(_) for _ in self.stars]) + f" ({self.timetocompletestar2} -- {astime(self.timetocompletestar2)})"

    def __getitem__(self, index):
        return self.stars[index]

    @property
    def starcount(self) -> int:
        return sum([_.starcount for _ in self.stars])#self.star1.starcount + self.star2.starcount


class Player(BaseObj):
    def __init__(self, score: dict, *, daycount=25, leaderboard):
        self.daycount = daycount
        self.days = {int(_): PlayerDay(score['completion_day_level'][_]) for _ in score['completion_day_level'].keys()}
        self.days.update({_: PlayerDay({}) for _ in range(1, daycount+1) if _ not in self.days})
        self.totalscore = 0
        self.laststar = int(score.get('last_star_ts', 0))
        self.globalscore = score['global_score']
        self.localscore = score['local_score']
        self.id = score['id']
        self.name = score['name'] or self.id
        self.pendingpoints = 0
        self.accumulatedtobiiscoretotal = 0
        self.position = None
        self.props = ""

    def __str__(self):
        days = [str(self.days[_]) for _ in sorted(self.days)]
        return f"{self.position:3} {self.name} ({self.id}) - {self.localscore}/{self.globalscore} " \
            + f"{'*' * self.stars} ({self.stars})" \
            + "\n\t* " + "\n\t* ".join(days)

    def __getitem__(self, index):
        return self.days[index]

    @property
    def stars(self):
        return sum([_.starcount for _ in self.days.values()])


class BoardStar():
    def __init__(self):
        self._topscore = 0
        self._besttime = None
        self.starsawarded = 0

    def __str__(self):
        return f"TS: {self.topscore} - SA: {self.starsawarded} - BT: {self.besttime}"

    @property
    def topscore(self) -> int:
        return self._topscore

    @topscore.setter
    def topscore(self, value: int):
        if value > self._topscore:
            self._topscore = value

    @property
    def besttime(self):
        return self._besttime

    @besttime.setter
    def besttime(self, value):
        if self._besttime == None or value < self._besttime:
            self._besttime = value


class LeaderBoard(BaseObj):
    def __init__(self, *,
            title: str,
            score: dict,
            year: str,
            highestday: int,
            namemap: dict,
            global_scores: dict):
        self.year = year
        self.title = title
        self.score = score
        self.boardid = score['owner_id']
        self.players = [Player(_, daycount=highestday, leaderboard=self) for _ in score['members'].values()]
        self.global_scores = global_scores

        if namemap:
            for p in [_ for _ in self.players if _.name in namemap]:
                p.name = f"{namemap[p.name]} ({p.name})"

        self.highestday = highestday
        self.excludezero = False

        self.days = {}

        for day in range(1, highestday+1):
            for player in self.players:
                self.days[day] = [BoardStar(), BoardStar()]
                for star in range(2):
                    self.days[day][star].starsawarded += player[day][star].starcount

    @property
    def today(self):
        return datetime.datetime.today().strftime("%Y-%m-%m %H:%M:%S")

    @property
    def ordered_players(self):
        return sorted(self.players,
            key=lambda x: (x.localscore, x.laststar, x.id),
            reverse=True)

    def day_excluded(self, day):
        # Fix this up later!
        # day 5 year 2018 is excluded,
        # but it makes sense to read this from somewhere.
        return day == 1

    def update_global_scores(self):
        logging.info("Updating global scores")
        for player in [_ for _ in self.players if _ in self.global_scores['names']]:
            for d in range(1, self.highestday+1):
                for star in range(2):
                    global_stars = self.global_scores['scores'][d]
                    pos = None
                    if player.name in global_stars:
                        pos = global_stars.index(player.name)
                    elif player.id in global_stars:
                        pos = global_stars.index(player.id)
                    if pos:
                        points = 101 - pos
                        logging.info(f"{player.name} scored {points} points on day {d} (star {star}), year {self.year}")
                        player[d][star].globalscore = points

    def post_process_stats(self) -> None:
        logging.info("Post processing")
        if self.excludezero:
            player_count = len([_ for _ in self.players if _.starcount > 0])
        else:
            player_count = len(self.players)

        laststar = {p:0 for p in self.players}

        for day in range(1, self.highestday + 1):
            publish_time = int(datetime.datetime(year=int(self.year), month=12, day=day, hour=6).timestamp())
            for player in self.players:
                for star in range(2):
                    thestar = player[day][star]
                    if thestar.completed:
                        thestar.timetocomplete = thestar.completiontime - publish_time
                        timespan = thestar.completiontime - publish_time
                        lasttime = 0 if day == 1 else player[day-1][1].accumulatedtimetocomplete
                        if lasttime is not None:
                            thestar.accumulatedtimetocomplete = lasttime + timespan
                            self.days[day][star].besttime = timespan
                    else:
                        player.pendingpoints += player_count - self.days[day][star].starsawarded
            # Now loop again and resolve board offsets etc
            # for day in range(1, self.highestday + 1):
            for star in range(2):
                ordered_players = sorted([_ for _ in self.players if _[day][star].completed],
                    key=lambda x: (x[day][star].completiontime, laststar.get(x, 0)))

                for player in sorted(self.players,
                        key=lambda x: (x[day][star].completiontime or -1, laststar.get(x, 0))):
                    thestar = player[day][star]
                    if thestar.completed:
                        index = ordered_players.index(player)

                        # Handle ties by setting index to the same as the player just ahead with the same completion time.
                        if index > 0 and thestar.completiontime == ordered_players[index-1][day][star].completiontime:
                            index = ordered_players[index-1][day][star].position - 1
                        thestar.position = index + 1
                        # print(f"{player.name} {day}/{star}: {player[day][star].position} -- {thestar.position}")

                        if not self.day_excluded(day):
                            player.totalscore += player_count - index
                            player.accumulatedtobiiscoretotal += index
                        thestar.offsetfromwinner = thestar.completiontime - publish_time - self.days[day][star].besttime
                        laststar[player] = thestar.completiontime
                    else:
                        if not self.day_excluded(day):
                            player.accumulatedtobiiscoretotal += len(self.players)

                    thestar.accumulatedscore = player.totalscore
                    self.days[day][star].topscore = player.totalscore
                    thestar.accumulatedtobiiscore = player.accumulatedtobiiscoretotal
                    # Why set localscore to totalscore? Are both properties needed? Will they ever differ?
                    player.localscore = player.totalscore

            for star in range(2):
                ordered_players = sorted([_ for _ in self.players if _[day][star].accumulatedscore > 0],
                    key=lambda x: x[day][star].accumulatedscore,
                    reverse=True)
                for player in self.players:
                    if player in ordered_players:
                        index = ordered_players.index(player)
                    else:
                        index = -1
                    # Handle ties
                    if index > 0 and player[day][star].accumulatedscore == ordered_players[index-1][day][star].accumulatedscore:
                        player[day][star].accumulatedposition = ordered_players[index-1][day][star].accumulatedposition
                    else:
                        player[day][star].accumulatedposition = index

        ordered_players = sorted([_ for _ in self.players],
            key=lambda x: x[day][star].accumulatedscore,
            reverse=True)
        for i, player in enumerate(ordered_players):
            ordered_players[i].position = i+1

        # for p in sorted(ordered_players, key=lambda x: x.totalscore, reverse=True):
        #     print(f"{p.name:<20} - {p[day][star].completiontime} - {p.totalscore}")

        for day in range(1, self.highestday+1):
            players = sorted([_ for _ in self.players if _[day].starcount == 2],
                key=lambda x: x[day].timetocompletestar2)
            for i, player in enumerate(players):
                player[day].star2pos = i+1
                if i > 0 and player[day].timetocompletestar2 == players[i-1][day].timetocompletestar2:
                    player[day].star2pos = i
            for player in [_ for _ in self.players if  _[day].starcount != 2]:
                player[day].star2pos = len(self.players)+1

    def leaderboard_data(self):
        res = []
        for i, p in enumerate(self.ordered_players):
            player_data = [i, p.name, p.totalscore, p.globalscore, p.stars, p.accumulatedtobiiscoretotal]
            for d in range(1, self.highestday+1):
                for star in range(2):
                    player_data.append(p[d][star].position if p[d][star].position else -1)
            res.append(player_data)
        return res



class GlobalListRepresentation(scores.DataRepresentation):
    def __init__(self, year: str, day: str):
        super().__init__()
        self.day = day
        self.year = year

    def filename(self):
        return f"global_{self.year}_{self.day}.html"

    def url(self):
        return f"https://adventofcode.com/{self.year}/leaderboard/day/{self.day}"


class ScoreboardRepresentation(scores.DataRepresentation):
    def __init__(self, boardid: str, year: str = "2020"):
        super().__init__()
        self.boardid = boardid
        self.year = year
        logging.debug(f"ScoreboardRepresentation: {self.filename()} -- {self.url()}")

    def filename(self):
        return f"{self.boardid}_{self.year}.json"

    def url(self):
        return f'https://adventofcode.com/{self.year}/leaderboard/private/view/{self.boardid}.json'


if __name__ == "__main__":
    import aocgen
    raise Exception("This is just a module!")

