# IEM India

Every beginner wired earphone you can buy in India under ₹10,000, on one chart. All 415 of them. Go poke at it.

**Play here:** _link going up shortly_

## Things to try

- Flip between 3.5 mm and Type-C and watch the dots rearrange.
- Put price along the bottom and sound up the side. Look for the part where paying more gets you better sound. Take your time.
- Hover a dot to see which earphone it is.
- Swap the axes for anything else: warm against bright, how many people measured it, what comes in the box.
- Think my ranking is wrong? Open **Explore**, drag the sliders and build your own.
- Still think it is wrong? Open **See the data**, download the CSV and make your own chart. If yours is better, send it to me.

## What is in here

- `site/` is the website. Astro with Svelte islands: every page is plain HTML and only the interactive bits ship JavaScript, so it stays quick on a phone.
- `study/` is the Python that built the dataset, step by step, plus the Excel master list with editable weights.

The raw downloads are not in the repo. They are other people's store catalogues and measurements, so only the numbers derived from them are published. Each script says at the top what it reads and where that came from.

## Standing on other people's work

- **Measurements:** the independent measurers who publish on squig.link. Every one is credited by name on the site's About page.
- **Compilation:** the open-source [Squig-Rank](https://github.com/PEQHUB/Squig-Rank) project.
- **Scoring model:** Olive, Welti and Khonsaripour, the Harman in-ear preference model, AES 2017.
- **Prices, specs and photos:** Headphone Zone, The Audio Store and Concept Kart. Specs are as claimed by the store.

## The small print

Made by [Jiyan Bhatt](https://www.linkedin.com/in/jiyanbhatt/) over a Diwali break. Not a shop, not sponsored, no affiliate links. Prices and stock were read on 11 November 2026 and will have moved since.

Code is MIT licensed. If you reuse the data, please credit the measurers the same way the site does.
