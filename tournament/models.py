from django.db import models
import random

class Player(models.Model):
    tournament = models.ForeignKey("Tournament", on_delete=models.CASCADE)
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
    opponent_match_win_percentage = models.FloatField(default=100/3)
    opponent_game_win_percentage = models.FloatField(default=100/3)
    game_win_percentage = models.FloatField(default=100/3)
    sort_key = models.CharField(max_length=200)
    # add dropping
    # add win/draws/losses

    def match_win_percentage(self):
        if self.opponents.count() == 0:
            return 100/3
        else:
            return max(100/3, (self.match_points - self.bye_count*3)/(self.opponents.count()*3.0)*100)

    def update_opponent_tiebreakers(self):
        value = 0.0;
        for opp in self.opponents.all():
            value += opp.match_win_percentage()
        if self.opponents.count() == 0:
            self.opponent_match_win_percentage = 100/3
        else:
            self.opponent_match_win_percentage = max(100/3, value/self.opponents.count())

        value = 0.0
        for opp in self.opponents.all():
            value += opp.game_win_percentage
        if self.opponents.count() == 0:
            self.opponent_game_win_percentage = 100/3
        else:
            self.opponent_game_win_percentage = max(100/3, value/self.opponents.count())
        self.save()

    def record_result(self, other, wins, draws, games):
        self.opponents.add(other);
        if wins > games - wins - draws:
            self.match_points += 3;
        elif wins == games - wins - draws:
            self.match_points += 1;
        self.game_points += 3*wins + draws
        self.games_played += games
        self.game_win_percentage = max(100/3, self.game_points/(self.games_played*3.0)*100)
        self.save()

class Table(models.Model):
    number = models.SmallIntegerField()
    current_round = models.ForeignKey("Round", on_delete=models.CASCADE)
    player_a = models.ForeignKey("Player", on_delete=models.CASCADE, related_name="+")
    player_b = models.ForeignKey("Player", on_delete=models.CASCADE, related_name="+")
    good_match = models.BooleanField(default=True)
    reported = models.BooleanField(default=False)
    player_a_wins = models.SmallIntegerField(default=0)
    player_b_wins = models.SmallIntegerField(default=0)
    draws = models.SmallIntegerField(default=0)

class Round(models.Model):
    number = models.SmallIntegerField()
    tournament = models.ForeignKey("Tournament", on_delete=models.CASCADE)
    player_list = models.ManyToManyField("Player")
    all_good = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    bye = models.SmallIntegerField(default=-1)

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
            t = Table(number=table_index, current_round=self, player_a=sorted_players[i-1], player_b=sorted_players[i], good_match=not(sorted_players[i-1] in sorted_players[i-1].opponents.all()))
            self.all_good = self.all_good and t.good_match
            t.save()
            table_index += 1
        if len(sorted_players)%2 == 1:
            self.bye = pairing_sort[-1].pk
        self.save()

    def all_good_check(self):
        if not self.completed:
            self.all_good = True
            for table in self.table_set.all():
                table.good_match = not(table.player_a in table.player_b.opponents.all())
                self.all_good = self.all_good and table.good_match
                table.save()
            self.save()
        return self.all_good

    def all_done_check(self):
        for table in self.table_set.all():
            if not(table.reported):
                return False
        return True

    def update_player_standings(self):
        #record_result(self, other, wins, draws, games):
        if self.bye >= 0:
            pbye = player_list.get(pk=self.bye)
            pbye.match_points += 3
            pbye.bye_count += 1
            pbye.save()
        for table in self.table_set.all():
            table.player_a.record_result(table.player_b, table.player_a_wins, table.draws, table.player_a_wins+table.player_b_wins+table.draws)
            table.player_b.record_result(table.player_a, table.player_b_wins, table.draws, table.player_a_wins+table.player_b_wins+table.draws)
        #update_opponent_tiebreakers(self):
        for p in self.player_list.all():
            p.update_opponent_tiebreakers()
        
    def uncomplete_round(self):
        if self.bye >= 0:
            pbye = player_list.get(pk=self.bye)
            pbye.match_points -= 3
            pbye.bye_count -= 1
            pbye.save()
        for table in self.table_set.all():
            table.player_a.opponents.remove(table.player_b)
            if table.player_a_wins > table.player_b_wins:
                table.player_a.match_points -= 3
            elif table.player_a_wins == table.player_b_wins:
                table.player_a.match_points -= 1
            table.player_a.game_points -= 3*table.player_a_wins + table.draws
            table.player_a.games_played -= table.player_a_wins + table.player_b_wins + table.draws
            if table.player_a.games_played > 0:
                table.player_a.game_win_percentage = max(100/3, table.player_a.game_points/(table.player_a.games_played*3.0)*100)
            else:
                table.player_a.game_win_percentage = 100/3
            table.player_a.save()
            
            table.player_b.opponents.remove(table.player_a)
            if table.player_b_wins > table.player_a_wins:
                table.player_b.match_points -= 3
            elif table.player_a_wins == table.player_b_wins:
                table.player_b.match_points -= 1
            table.player_b.game_points -= 3*table.player_b_wins + table.draws
            table.player_b.games_played -= table.player_a_wins + table.player_b_wins + table.draws
            if table.player_b.games_played > 0:
                table.player_b.game_win_percentage = max(100/3, table.player_b.game_points/(table.player_b.games_played*3.0)*100)
            else:
                table.player_b.game_win_percentage = 100/3
            table.player_b.save()
        self.completed = False
        self.save()

class Tournament(models.Model):
    name = models.CharField(max_length=200)
    player_name_space = models.SmallIntegerField(default=0)
    last_modified = models.DateTimeField(auto_now=True)

    def register(self, name):
        p = Player(name=name, tournament=self)
        p.save()
        if len(name)+1 > self.player_name_space:
            self.player_name_space = len(name) + 1
            self.save()

    def start_next_round(self):
        r = Round(number=Round.objects.filter(tournament=self).count()+1,tournament=self)
        r.save()
        r.initialize(self.player_set.all())
        r.save()
        return r