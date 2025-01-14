


endpoint = main_api.get_endpoint("results_by_tournament")


match_options = (
    "match_id",
    "match_date",
    "main_team_id",
    "opponent_id",
    "tour",
    "status",
    "goals_scored",
    "goals_conceded",
    "score",
)


for t in tournaments:

    date = date_to_check.strftime(main_api.DATE_FORMAT)

    tournament_api_obj = main_api_model.get_tournament_api_obj_by_tournament(t)

    if not tournament_api_obj:
        continue

    tournament_api_id = tournament_api_obj.api_football_id
    tournament_api_season = main_api_model.get_tournament_api_season_by_tournament(
        t
    )

    payload = main_api.get_payload(
        task="results_by_tournament",
        tournament_api_id=tournament_api_id,
        tournament_api_season=tournament_api_season,
        date=date,
    )

    response = main_api.send_request(endpoint, payload)

    if response["errors"]:
        return HttpResponse("Response Errors: please check the logs for details")

    utils.increase_api_requests_count()

    matches = api_parser.parse_matches(response)

    for match in matches:

        match_data = {}

        for option in match_options:
            try:
                match_data[option] = getattr(api_parser, "get_" + option)(match)
            except AttributeError:
                message = f"get_{option} method should be realized in {api_parser.__class__.__name__}"
                logger.error(message)
                continue
            except ApiParserError:
                continue

        team1 = main_api_model.get_team_by_api_id(match_data["main_team_id"])
        team2 = main_api_model.get_team_by_api_id(match_data["opponent_id"])

        if not team1 or not team2:
            # todo We need to add this team into DB using specific API request
            # but not at the same time, the task needs to be added to the queue
            continue

        # поле is_moderated задумывалось как требование ручной корректировки данных
        # в админке т.к. если матч заканчивался по пенальти не было данных из АПИ
        # Решение - купить платный сервис АПИ
        # Пока используем только регулярные чемпионаты поэтому
        # is_moderated можно выставить в True
        is_moderated = True

        api_match_record = main_api_model.get_match_record(match_data["match_id"])

        if api_match_record:
            match_record = api_match_record.content_object

            data_for_update = {
                "date": match_data["match_date"],
                "status": match_data["status"],
                "goals_scored": match_data["goals_scored"],
                "goals_conceded": match_data["goals_conceded"],
                "is_moderated": is_moderated,
                "result": match_record.result,
                "points_received": match_record.points_received,
            }

            for field, value in data_for_update.items():
                setattr(match_record, field, value)

            match_record.save()
        else:
            m = t_models.Match()

            m.date = match_data["match_date"]
            m.main_team = team1
            m.opponent = team2
            m.status = match_data["status"]
            m.goals_scored = match_data["goals_scored"]
            m.goals_conceded = match_data["goals_conceded"]
            m.tournament = t
            m.tour = match_data["tour"]
            m.stage = None
            m.is_moderated = is_moderated
            m.score = match_data["score"]
            m.temporary_match_id = match_data["match_id"]
            m.save()