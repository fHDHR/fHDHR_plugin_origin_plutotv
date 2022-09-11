from functools import reduce
import datetime

import fHDHR.tools


class Plugin_OBJ():

    def __init__(self, channels, plugin_utils):
        self.plugin_utils = plugin_utils

        self.channels = channels

        self.origin_name = plugin_utils.origin_name

        self.base_api_url = 'https://api.pluto.tv'

    def xmltime_pluto(self, inputtime):
        xmltime = inputtime.replace('Z', '+00:00')
        xmltime = datetime.datetime.fromisoformat(xmltime)
        return xmltime

    def xmltimestamp_pluto(self, inputtime):
        return self.xmltime_pluto(inputtime).timestamp()

    def duration_pluto_minutes(self, induration):
        return ((int(induration))/1000/60)

    def update_epg(self):
        programguide = {}

        xtime = datetime.datetime.utcnow()

        guide_time = {
                    "start": str(xtime.strftime('%Y-%m-%dT%H:00:00')),
                    "end": str((xtime + datetime.timedelta(hours=8)).strftime('%Y-%m-%dT%H:00:00')),
                    }

        epgurl = '%s/v2/channels?start=%s.000Z&stop=%s.000Z' % (self.base_api_url, guide_time["start"], guide_time["end"])

        result = self.plugin_utils.web.session.get(epgurl).json()

        for c in result:

            if (c["isStitched"]
               and c["visibility"] in ["everyone"]
               and not c['onDemand']
               and c["name"] != "Announcement"):

                cdict = fHDHR.tools.xmldictmaker(c, ["name", "number", "_id", "timelines", "colorLogoPNG"], list_items=["timelines"])

                chan_obj = self.channels.get_channel_obj("origin_id", cdict["_id"], self.plugin_utils.namespace)
                if chan_obj:

                    if str(chan_obj.number) not in list(programguide.keys()):

                        programguide[str(chan_obj.number)] = chan_obj.epgdict

                    for program_item in cdict["timelines"]:

                        progdict = fHDHR.tools.xmldictmaker(program_item, ['_id', 'start', 'stop', 'title', 'episode'])
                        episodedict = fHDHR.tools.xmldictmaker(program_item['episode'], ['duration', 'poster', '_id', 'rating', 'description', 'genre', 'subGenre', 'name'])

                        if episodedict["duration"]:
                            episodedict["duration"] = self.duration_pluto_minutes(episodedict["duration"])
                            genres = [k.split(" \\u0026 ") for k in [episodedict.get(k) for k in ("genre", "subGenre")] if k is not None]
                            genres = reduce(lambda x,y: x+y, genres)
                            if 'clip' in episodedict and 'originalReleaseDate' in episodedict['clip']:
                                releaseyear = self.xmltime_pluto(episodedict['clip']['originalReleaseDate']).year

                            clean_prog_dict = {
                                                "time_start": self.xmltimestamp_pluto(progdict["start"]),
                                                "time_end": self.xmltimestamp_pluto(progdict["stop"]),
                                                "duration_minutes": episodedict["duration"],
                                                "thumbnail": None,
                                                "title": progdict.get("title") or "Unavailable",
                                                "sub-title": episodedict.get("name") or "Unavailable",
                                                "description": episodedict.get("description") or "Unavailable",
                                                "rating": episodedict.get("rating") or "N/A",
                                                "episodetitle": episodedict.get("name") or "Unavailable",
                                                "releaseyear": releaseyear,
                                                "genres": genres,
                                                "seasonnumber": episodedict.get("season") or "Unavailable",
                                                "episodenumber": episodedict.get("number") or "Unavailable",
                                                "isnew": episodedict.get("liveBroadcast") or False,
                                                "id": str(episodedict['_id'] or "%s_%s" % (chan_obj.dict['origin_id'], self.xmltimestamp_pluto(progdict["start"])))
                                                }
                            try:
                                thumbnail = episodedict["poster"]["path"].split("?")[0]
                            except TypeError:
                                thumbnail = None
                            clean_prog_dict["thumbnail"] = thumbnail

                            if not any((d['time_start'] == clean_prog_dict['time_start'] and d['id'] == clean_prog_dict['id']) for d in programguide[chan_obj.number]["listing"]):
                                programguide[str(chan_obj.number)]["listing"].append(clean_prog_dict)

        return programguide
