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

class GameInline(admin.TabularInline):
    model = Game
    extra = 0
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super(GameInline, self).get_formset(request, obj, **kwargs)
        
        initial = []
        
        if request.method == "GET":
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
    
class RoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'tournament', 'round_date')
    list_filter = ['round_date']
    date_hierarchy = 'round_date'
    search_fields = ['name']
    ordering = ['-round_date']
    inlines = [GameInline]
    
admin.site.register(Round, RoundAdmin)
