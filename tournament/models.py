from django.db import models

class Player(models.Model):
    tournament = models.ForeignKey("Tournament")
    name = models.CharField(max_length=200)
    opponents = models.ManyToManyField("self")
    # Tiebreakers
    # match points
    # opp MW%
    # GW%
    # opp GW%
    match_points = models.SmallIntegerField(default=0)
    game_points = models.SmallIntegerField(default=0)
    games_played = models.SmallIntegerField(default=0)
    bye_count = models.SmallIntegerField(default=0)
    opponent_match_win_percentage = models.FloatField(default=1/3)
    opponent_game_win_percentage = models.FloatField(default=1/3)
    sort_key = models.CharField(max_length=200)

    def game_win_percentage(self):
        if self.games_played == 0:
            return 1/3
        else:
            return max(1/3, self.game_points/(self.games_played*3.0))

    def match_win_percentage(self):
        if len(self.opponents) == 0:
            return 1/3
        else:
            return max(1/3, (self.match_points - self.bye_count*3)/(len(self.opponents)*3.0))

    def update_opponent_tiebreakers(self):
        value = 0.0;
        for opp in self.opponents_set.all():
            value += opp.match_win_percentage()
        if len(self.opponents) == 0:
            self.opponent_match_win_percentage = 1/3
        else:
            self.opponent_match_win_percentage = max(1/3, value/len(self.opponents))

        value = 0.0
        for opp in self.opponents_set.all():
            value += opp.game_win_percentage()
        if len(self.opponents) == 0:
            self.opponent_game_win_percentage = 1/3
        else:
            self.opponent_game_win_percentage = max(1/3, value/len(self.opponents))
        self.save()

    def record_result(self, other, wins, draws, games):
        self.opponents.append(other);
        if wins == 2:
            self.match_points += 3;
        elif wins == games - wins - draws:
            self.match_points += 1;
        self.game_points += 3*wins + draws
        self.games_played += games
        self.save()

class Table(models.Model):
    number = models.SmallIntegerField()
    round = models.ForeignKey("Round", on_delete=models.CASCADE)
    player_a = models.ForeignKey("Player")
    player_b = models.ForeignKey("Player")
    good_match = models.BooleanField(default=True)
    reported = models.BooleanField(default=False)
    player_a_wins = models.SmallIntegerField(default=0)
    player_b_wins = models.SmallIntegerField(default=0)
    draws = models.SmallIntegerField(default=0)

class Round(models.Model):
    number = models.SmallIntegerField()
    tournament = models.ForeignKey("Tournament")
    player_list = models.ManyToManyField("Player")
    all_good = models.BooleanField(default=True)
    bye = models.ForeignKey("Player")

    def initialize(self, player_list):
        key_strings = ["a"*x for x in range(len(player_list))]
        for p in player_list:
            c = random.choice(key_strings)
            key_strings.remove(c)
            p.sort_key = f"{p.match_points}{c}"
            p.save()
            self.player_list.add(p)
        table_index = 1
        sorted_players = self.player_list.order_by("-sort_key")
        for i in range(1,len(sorted_players),2):
            t = Table(number=table_index, round=self, player_a=sorted_players[i-1], player_b=sorted_players[i], good_match=not(sorted_players[i-1] in sorted_players[i-1].opponents.all()))
            self.all_good = self.all_good and t.good_match
            t.save()
            table_index += 1
        if len(sorted_players)%2 == 1:
            self.bye = pairing_sort[-1]
        self.save()

    def all_good_check(self):
        self.all_good = True
        for table in self.tables.all():
            table[2] = not(table[0] in table[1].opponents.all())
            self.all_good = self.all_good and table[2]
        return self.all_good

    def all_done_check(self):
        for table in self.tables.all():
            if not(table[3]):
                return False
        return True

    def update_player_standings(self):
        #record_result(self, other, wins, draws, games):
        if self.bye is not None:
            self.bye.match_points += 3
            self.bye.bye_count += 1
            self.bye.save()
        for table in self.tables.all():
            table.player_a.record_result(table.player_b, table.player_a_wins, table.draws, table.player_a_wins+table.player_b_wins+table.draws)
            table.player_b.record_result(table.player_a, table.player_b_wins, table.draws, table.player_a_wins+table.player_b_wins+table.draws)
        #update_opponent_tiebreakers(self):
        for p in self.player_list.all():
            p.update_opponent_tiebreakers()

class Tournament(models.Model):
    name = models.CharField(max_length=200)
    player_name_space = models.SmallIntegerField()

    def register(self, name):
        p = Player(name=name, tournament=self)
        p.save()
        if len(name)+1 > self.player_name_space:
            self.player_name_space = len(name) + 1

    def start_next_round(self):
        r = Round(number=self.round_set.count()+1,tournament=self)
        r.initialize(self.player_set.all())
        r.save()
        return r