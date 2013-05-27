from django.contrib import admin
from tournaments.models import Player, Tournament, Round, Game
from django import forms
from django.utils.functional import curry
import math

class PlayerAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'country', 'fide_id', 'fide_title', 'initial_rating')
        }),
    )
    list_display = ('name', 'fide_title', 'country', 'rating', 'fide_id', 'register_date')
    search_fields = ['name'],
    ordering = ['name']
    
admin.site.register(Player, PlayerAdmin)

# Sort players alphabetically
class PlayerInlineForm(forms.ModelForm):
    player = forms.ModelChoiceField(queryset=Player.objects.order_by('name'))
    player.label = 'Player'
    
class PlayerInline(admin.TabularInline):
    model = Tournament.players.through
    form = PlayerInlineForm
    extra = 0

class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'start_date', 'end_date', 'players_count', 'add_round_link')
    list_filter = ['start_date']
    date_hierarchy = 'start_date'
    search_fields = ['name']
    ordering = ['-start_date']
    inlines = [PlayerInline]
    exclude = ['players']
    admin.site.disable_action('delete_selected')
    class Media:
        css = { "all" : ("css/additional_admin.css",) }    
    
    def add_round_link(self, tour):
        return '{0:d} (<a href="../round/add' \
            '?tournament={1:d}&name={2:s}">add new</a>)'.format(
                                                                tour.round_set.count(), 
                                                                tour.id,
                                                                "Round " + str(tour.round_set.count() + 1)
                                                                )
    add_round_link.short_description = 'Rounds'
    add_round_link.allow_tags = True    

admin.site.register(Tournament, TournamentAdmin)


class GameInLineFormAdmin(forms.ModelForm):
    player = forms.ModelChoiceField(queryset=Player.objects.order_by('name'))
    player.label = 'Player'
    opponent = forms.ModelChoiceField(queryset=Player.objects.order_by('name'))
    opponent.label = 'Opponent'
    
    def clean(self):
        cleaned_data = super(GameInLineFormAdmin, self).clean()
        player_score = cleaned_data.get("player_score")
        opponent_score = cleaned_data.get("opponent_score")
        status = cleaned_data.get("status")
        
        total_score = float(player_score) + float(opponent_score)
        if status == 'planned' and total_score > 0:
            self._errors["status"] = self.error_class([u'Planned status is not allowed if game has score'])
            del cleaned_data["status"]
            
        elif status != 'planned' and total_score == 0:
            self._errors["status"] = self.error_class([u'Planned status must be set if game has not score'])
            del cleaned_data["status"]

        elif status != 'planned' and (total_score == 0.5 or total_score > 1):
            self._errors["status"] = self.error_class([u'Incorrect score'])
            del cleaned_data["status"]
            
        return cleaned_data
            
class GameInline(admin.TabularInline):
    model = Game
    form = GameInLineFormAdmin
    extra = 0
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super(GameInline, self).get_formset(request, obj, **kwargs)
        
        initial = []
        
        if request.method == "GET" and obj is None and request.GET.has_key('tournament'):
            tournament = Tournament.objects.get(pk=request.GET['tournament'])
            players = tournament.players.order_by('-rating')
            game_count = int(math.ceil(float(players.count()) / 2.0))
            
            formset.extra = game_count
            
            if tournament.round_set.count() == 0:
                for player in players[:game_count]:
                    initial.append({'player': player,
                                    'player_score': 0,
                                    'opponent': players[game_count + len(initial)],
                                    'opponent_score': 0,
                                    })
                pass
        
        formset.__init__ = curry(formset.__init__, initial=initial)
        
        return formset

class RoundFormAdmin(forms.ModelForm):
    def clean(self):
        cleaned_data = super(RoundFormAdmin, self).clean()
        
        tour = cleaned_data.get("tournament")
        if tour is not None:
            if self.instance.pk and tour.round_set.count() > 0:
                prev_round = tour.round_set.order_by("-round_date")[0]
                if prev_round.pk != self.instance.pk:
                    if prev_round.game_set.count() == 0:
                        raise forms.ValidationError("The previous round doesn't have any games.")
                    elif prev_round.game_set.filter(status="planned").count() > 0:
                        raise forms.ValidationError("The previous round has unfinished games.")

        return cleaned_data
            
    pass
    
class RoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'tournament', 'round_date')
    list_filter = ['round_date']
    date_hierarchy = 'round_date'
    search_fields = ['name']
    ordering = ['-round_date']
    inlines = [GameInline]
    form = RoundFormAdmin
    
    class Media:
        css = { "all" : ("css/additional_admin.css",) }
             
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}    
    
admin.site.register(Round, RoundAdmin)
