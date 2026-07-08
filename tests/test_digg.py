from fli.digg import parse_rankings, parse_top_followers


RANKINGS_HTML = """
<div class="group relative"><a aria-label="Open Andrej Karpathy profile"
href="/u/x/karpathy"></a>
<span data-slot="ranked-avatar-rank">1</span>
<img src="https://cdn/authors/33836629/avatar-a.jpg" alt="Andrej Karpathy"/>
<h2 class="x">Andrej Karpathy</h2>
<a href="https://x.com/karpathy">@<!-- -->karpathy</a>
<a title="View Research Engineer rankings" href="/tech/x/rankings?tag=research-engineer">
<span>RESEARCH ENGINEER</span></a>
<span title="#1 in the AI cohort">AI</span>
<span class="font-semibold text-foreground">758</span><span class="text-muted-foreground"> <!-- -->Tech ranked followers</span>
<span class="font-semibold text-foreground">10.000</span><span class="text-muted-foreground"> gravity</span>
<p class="line-clamp-2 font-mono">I like training large deep neural nets.</p>
</div>
"""


PROFILE_HTML = """
<h2>Top followers</h2>
<a aria-label="Open Yann LeCun profile" class="group block active:scale-[0.99]"
href="/u/x/ylecun">
<img src="https://cdn/authors/48008938/avatar-x.jpg" alt="Yann LeCun"/>
<span>#3</span>
<p>Yann LeCun</p>
<p>@<!-- -->ylecun</p>
<p>Professor at NYU &amp; Executive Chairman at AMI Labs.</p>
</a>
<script>self.__next_f.push([1,"44:[\\"$\\",\\"div\\",null,{\\"children\\":[\\"$\\",\\"$L46\\",null,{\\"vibeTopics\\":{\\"vibeDistribution\\":{\\"teaching\\":22.6,\\"informing\\":25.8},\\"topicDistribution\\":{\\"LLM Training\\":26.1,\\"AI Agents\\":20.1},\\"tweetCount\\":200,\\"authorXId\\":\\"33836629\\",\\"username\\":\\"karpathy\\"}}]}]"])</script>
<script>self.__next_f.push([1,"77:[\\"$\\",\\"$L78\\",null,{\\"username\\":\\"karpathy\\",\\"initialCount\\":50,\\"totalCount\\":1658}]"])</script>
"""


def test_parse_rankings():
    rows = parse_rankings(RANKINGS_HTML)
    assert rows == [
        {
            "rank": 1,
            "username": "karpathy",
            "digg_profile_username": "karpathy",
            "display_name": "Andrej Karpathy",
            "role": "Research Engineer",
            "cohort": "AI",
            "tech_ranked_followers": 758,
            "gravity": 10.0,
            "bio": "I like training large deep neural nets.",
            "x_id": "33836629",
            "digg_url": "https://digg.com/u/x/karpathy",
            "x_url": "https://x.com/karpathy",
        }
    ]


def test_parse_top_followers():
    parsed = parse_top_followers(PROFILE_HTML, "karpathy")
    assert parsed["initial_count"] == 50
    assert parsed["total_count"] == 1658
    assert parsed["vibe_topics"] == {
        "vibeDistribution": {"teaching": 22.6, "informing": 25.8},
        "topicDistribution": {"LLM Training": 26.1, "AI Agents": 20.1},
        "tweetCount": 200,
        "authorXId": "33836629",
        "username": "karpathy",
    }
    assert parsed["followers"] == [
        {
            "rank": 3,
            "username": "ylecun",
            "digg_profile_username": "ylecun",
            "display_name": "Yann LeCun",
            "bio": "Professor at NYU & Executive Chairman at AMI Labs.",
            "x_id": "48008938",
            "digg_url": "https://digg.com/u/x/ylecun",
            "x_url": "https://x.com/ylecun",
        }
    ]
