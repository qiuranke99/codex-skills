# TVC Query Lanes

Run multiple lanes. Single-query searching is the main cause of weak TVC reference lists.

## Lane 1: Direct Category

Use when the brief has a clear product or service category.

```text
site:vimeo.com ("<category>" OR "<synonym>") ("commercial" OR "campaign film" OR "product film" OR "beauty film" OR "TVC") -review -tutorial -unboxing -stock
site:youtube.com/watch ("<category>" OR "<synonym>") ("commercial" OR "ad" OR "TVC" OR "campaign") -review -routine -haul -shorts
site:xinpianchang.com (<品类> OR <同义词>) (TVC OR 广告片 OR 产品片 OR 宣传片) (模特 OR 使用 OR 质感 OR 特写) -测评 -教程 -开箱 -直播 -带货
```

Body-oil variants:

```text
("body oil" OR "dry oil" OR "skin oil" OR "bath and body oil" OR "vitamin E body oil")
(护体油 OR 身体油 OR 身体护理油 OR 护肤油 OR 干油 OR 维E身体油)
```

## Lane 2: Competitor Brand

Use brand seeds to escape generic search noise. Do not assume every seed has a usable TVC.

```text
("<brand>" OR "<competitor>") ("<product>" OR "<category>") ("commercial" OR "campaign" OR "film" OR "TVC")
"<brand>" "<campaign title>" director
"<brand>" "<product>" "Vimeo"
"<brand>" "<product>" "YouTube"
```

Body-oil seeds can include NUXE, Bio-Oil, Palmer's, L'Occitane Almond, OSEA, Clarins, Neutrogena, NIVEA, Weleda, Caudalie, Sol de Janeiro, and similar market-tier brands.

## Lane 3: Creator, Director, Production

Use when the category lane is noisy or when you need TVC-grade craft.

```text
site:vimeo.com (beauty OR skincare OR "body care") ("directed by" OR director OR DOP OR "production company") ("commercial" OR TVC)
site:xinpianchang.com (美妆 OR 护肤 OR 身体护理) (导演 OR 摄影指导 OR 制作公司) (TVC OR 广告片)
site:lbbonline.com (beauty OR skincare OR cosmetics OR "body care") ("campaign film" OR director OR "production company")
site:shots.net (beauty OR skincare OR cosmetics OR "body care") (commercial OR campaign)
```

When a good creator is found, search their name plus the category:

```text
"<director name>" "<brand>" skincare
"<production company>" beauty film
"<DOP name>" "<category>" commercial
"<colour house>" beauty commercial
```

## Lane 4: Visual Mechanism

Use when the brief asks for a specific sensory or craft problem.

```text
("oil texture" OR "skin glow" OR "body oil application" OR "hand application" OR "macro skin" OR droplet OR "viscous liquid") ("commercial" OR "beauty film" OR "product film")
(油质感 OR 液体质感 OR 肌肤光泽 OR 涂抹 OR 手部特写 OR 液滴 OR 微距) (护肤 OR 美妆 OR 身体护理) (广告片 OR 产品片 OR TVC)
("window light" OR "bathroom light" OR "linen" OR "skin highlight") ("body care" OR skincare) ("commercial" OR "campaign film")
```

Mechanism results are often analogies. Label them as such.

## Lane 5: Original-Source Recovery

Use when a promising clue comes from a weak source.

1. Extract hard facts: exact title, brand, product, director, production company, agency, DOP, editor, colour house, upload account, end-frame logo.
2. Search those facts in combinations:

```text
"<exact title>" "<brand>" director
"<brand>" "<campaign title>" "production company"
"<creator name>" "<brand>" "commercial"
"<brand>" "<product>" "directed by"
"<title>" site:vimeo.com
"<title>" site:youtube.com/watch
```

3. Keep the weak page in `unconfirmed_leads` until an original or professional source is verified.

## Anti-Noise Filters

English:

```text
-review -tutorial -"how to" -routine -haul -unboxing -try-on -dupe -affiliate -amazon -shop -price -stock -shutterstock -pond5 -videohive -template -mockup -AI -vlog -UGC -shorts
```

Chinese:

```text
-测评 -教程 -种草 -开箱 -带货 -直播 -购物 -旗舰店 -淘宝 -京东 -素材 -模板 -合集 -花絮 -幕后 -口播 -vlog -短视频
```

Use negative terms aggressively, but do not remove terms that are central to the category.

If Chinese appears garbled in the terminal or editor, reload these files as UTF-8 before copying the query. Do not transliterate Chinese category terms unless search results are clearly better in pinyin or English.

## Minimum Search Audit

Record:

- query lanes used;
- exact queries tried;
- platforms checked;
- source recovery attempts;
- hard exclusions;
- rejected patterns;
- unconfirmed leads;
- missing source tiers;
- next searches.
