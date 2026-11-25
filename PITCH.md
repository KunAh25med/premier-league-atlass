# Pitch kit (replace every [bracket] before sending)

## One line
380 matches, one island: the 2026/27 Premier League season seen as geography. Interactive, in English and Arabic.

## Email to partnerships@premierleague.com (send once)
**Subject:** Proposal: an interactive, bilingual geography atlas of the 2026/27 Premier League season

Dear Premier League partnerships team,

I am Ahmed Bahaa, a [your real job title], and I publish "Spatial Football Analytics". I have built an independent, interactive atlas that shows each gameweek as geography: where away fans travel, which matches kick off after sunset, derby distances, and which stadium each part of England is closest to. It runs in the browser, in English and Arabic.

Atlas: [URL]
60-second video: [video link]
Method and data notes: see "How it is calculated" at the bottom of the page.

I would value two things. First, your guidance on what use of the Premier League name, colours and fixture data is acceptable. Second, a conversation about whether a weekly Arabic-language gameweek atlas could complement your channels. I am not asking for an endorsement, and I will adapt to your advice, including moving to licensed data.

This is an independent project and is not affiliated with the Premier League.

Thank you for your time.
Ahmed Bahaa | [title] | [phone] | [LinkedIn] | [page URL]

## One-page summary (export to PDF)
- **What it is:** an atlas of all 380 fixtures of 2026/27, one gameweek at a time, on an interactive map.
- **What you can do:** choose a gameweek, play the matches one by one, open any club, see your club's next trip, watch the sun and floodlights at kick-off, compare derbies.
- **GIS inside:** geodesic distances, Voronoi territories, nearest-neighbour rivals, a distance-weighted travel centre, solar position per match, population catchments and road times (with real data files).
- **Languages:** English and Arabic (right-to-left).
- **Data and limits:** fixtures from the published list and the public feed; stadium coordinates approximate; population and road-time tabs are indicative until the real data files are loaded; the distance-versus-results chart is early data.
- **About me:** [two lines, your real background].
- **Contact:** [email] [phone] [links].

## 60-second video script
1. 0-5 s: "380 matches. One island. Where do they happen?" (the hero)
2. 5-15 s: Play the story: territories, then the gameweek's away trips.
3. 15-25 s: Match by match: the dot travels, the distance appears, the score shows.
4. 25-35 s: Daylight layer: the shadow of night crosses England; "5 of 10 matches see the sun set".
5. 35-45 s: Choose my club: next match, journey, light at kick-off.
6. 45-55 s: Season odyssey (on satellite if it is ready).
7. 55-60 s: "Every gameweek. English and Arabic." plus the link.
Record with the page's "Record clip", then convert to MP4: `ffmpeg -i clip.webm clip.mp4`.

## First four posts (regenerate the numbers from the page each week)
**LinkedIn (EN):** Where does the sun set on a Premier League Saturday? I built an interactive GIS atlas of the 2026/27 season: territories, away-day journeys, kick-off light and derby distances. Gameweek 11 as an example: Arsenal travel 393 km to Newcastle, and the sun sets during 5 of 10 matches. English and Arabic. [link] #GIS #FootballAnalytics #PremierLeague

**X (EN):** Gameweek 11 by geography: 2,343 km of away travel, 3 kick-offs after sunset, the sun sets during 5 matches. Interactive atlas, EN/AR: [link]

**Facebook (AR):** أطلس الدوري الإنجليزي بالجغرافيا: كام كيلومتر هتسافر جماهير كل ناد في الجولة؟ وأي مباريات هتتلعب بالكشافات لأن الشمس هتغرب؟ جرّب الخريطة التفاعلية بالعربي والإنجليزي: [رابط]

**X (AR), for the Arabic account later:** [لقطة من البطاقة] خريطة تفاعلية لجولة الدوري الإنجليزي بالعربي: الرحلات والمسافات والشمس عند صافرة البداية. [رابط]

## Arabic press paragraph
مشروع مستقل لتحليل نظم المعلومات الجغرافية يعرض كل جولة من الدوري الإنجليزي كخريطة تفاعلية: كم يقطع جمهور كل نادٍ، وأي المباريات تُلعب تحت الكشافات، وأقرب ملعبين في الدوري. متاح بالعربية والإنجليزية. [الرابط]

## Before you send
- Atlas hosted on a stable URL; real data files loaded (atlas, population, travel); stadium coordinates checked.
- Arabic reviewed by a native reader.
- No logos or crests anywhere; the independence notice is visible.
- Four weeks of posts published, with real engagement numbers in the email if you have them.

## Email to Esri and other GIS companies (one tailored email each)
**Subject:** Football as a spatial problem: an interactive atlas of the 2026/27 Premier League season

Hello [name or team],

I am Ahmed Bahaa, a [your real job title]. I built an independent interactive atlas of the 2026/27 Premier League that treats each gameweek as a spatial problem: Voronoi territories, the "contested ground" within a few kilometres of a territory border, distance-weighted travel centres, solar position at kick-off, population catchments and road-time rankings. The PostGIS queries behind the numbers are in the repository.

Atlas: [URL]
Repository: [GitHub URL]
60-second video: [video link]

I would welcome your feedback and, if it fits your channels, a mention or a conversation about presenting it as a sports-GIS case study. No obligation. I am also preparing a StoryMaps version.

Thank you,
Ahmed Bahaa | [title] | [links]

For MapTiler, Mapbox or Esri imagery, add one line: "The Season odyssey page uses your satellite imagery with attribution; I would be glad to share it."

## Short note for the official social pages (comment or DM, once, not to every page)
EN: Hi! I built an independent, interactive geography atlas of the 2026/27 season, in English and Arabic. Not affiliated, sharing in case it is useful for your Arabic-speaking fans: [link]
AR: أهلًا! عملت أطلسًا جغرافيًا تفاعليًا مستقلًا لموسم 2026/27 بالعربية والإنجليزية. غير تابع للدوري، وأشاركه لو كان مفيدًا لجماهيركم العربية: [رابط]

## Esri StoryMaps competition
Esri's 2026 ArcGIS StoryMaps competition showed a submission deadline of 11 December 2026. Check the official rules on esri.com/storymaps/contest first (who may enter, one story built in ArcGIS StoryMaps, and whether embedding an external app counts). "Contested ground" and "the sun sets during the match" fit a "see what others missed" story.

## Order of operations
1. Run the three pipelines. 2. Push to GitHub, enable Pages and the Action. 3. Check on a phone. 4. Record the video. 5. Post weekly. 6. After four weeks, send the one email to partnerships@premierleague.com. 7. In parallel, send the GIS emails and, if you enter, the StoryMaps entry.
