from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Tournament, Round, Table
import os


def index(request):
    if "player_names" in request.POST:
        player_names = request.POST["player_names"].split(os.linesep)
        t = Tournament(name=request.POST["t_name"])
        t.save()
        for pn in player_names:
            t.register(pn)
        t.start_next_round()
        return HttpResponseRedirect(reverse("tournament:detail", args=(t.id,)))
    context = {"tour_list":Tournament.objects.all().order_by("-last_modified")}
    return render(request, 'tournament/index.html', context)

def detail(request, tournament_id):
    t = Tournament.objects.get(pk=tournament_id)
    r = Round.objects.get(number=Round.objects.filter(tournament=t).count())
    if "table_edit" in request.POST:
        if int(request.POST["table_edit"]) >= 0:
            table = Table.objects.get(pk=request.POST["table_edit"])
            table.player_a_wins = request.POST[request.POST["table_edit"]+"a"]
            table.draws = request.POST[request.POST["table_edit"]+"d"]
            table.player_b_wins = request.POST[request.POST["table_edit"]+"b"]
            table.reported = True
            table.save()
        elif r.all_done_check() and not r.completed:
            r.update_player_standings()
            r.completed = True
            r.save()
        elif r.completed:
            r = t.start_next_round()


    context = {"tour_name":t.name, "tour_id":t.id, "round":r, "pairings":r.table_set.order_by("number")}
    if r.completed:
        context["stand_name"] = "as of the current round"
        context["standings"] = r.player_list.order_by("-match_points","-opponent_match_win_percentage","-game_win_percentage","-opponent_game_win_percentage")
    elif r.number > 1:
        context["stand_name"] = "as of the previous round"
        context["standings"] = Round.objects.get(number=r.number-1).player_list.order_by("-match_points","-opponent_match_win_percentage","-game_win_percentage","-opponent_game_win_percentage")
    return render(request, 'tournament/detail.html', context)
    
def edit_round(request, round_id):
    r = Round.objects.get(pk=round_id)
    if "choices" in request.POST:
        c = request.POST["choices"].split()
        t1 = Table.objects.get(pk=c[0][:-1])
        t2 = Table.objects.get(pk=c[1][:-1])
        if c[0][-1] == "a":
            p1 = t1.player_a
            if c[1][-1] == "a":
                t1.player_a = t2.player_a
                t2.player_a = p1
            else:
                t1.player_a = t2.player_b
                t2.player_b = p1
        else:
            p1 = t1.player_b
            if c[1][-1] == "a":
                t1.player_b = t2.player_a
                t2.player_a = p1
            else:
                t1.player_b = t2.player_b
                t2.player_b = p1
        t1.save()
        t2.save()
        r.all_good_check()
        
    context = {"round":r, "pairings":r.table_set.order_by("number")}
    return render(request, 'tournament/edit_round.html', context)

def undo_round(request, round_id):
    r = Round.objects.get(pk=round_id)
    r.uncomplete_round()
    return HttpResponseRedirect(reverse("tournament:detail", args=(r.tournament.id,)))