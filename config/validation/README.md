# Validation targets

`davidovic2026_table2.csv` is Table 2 ("Land-use changes in Natura 2000 site Kras (2002–2024)") of

> Davidović, D., Čuš, J., Ivajnšič, D. 2026: Land-use dynamics and grassland succession challenges in the
> Natura 2000 site Kras: The socioeconomic perspective. *Acta geographica Slovenica* 66(1), 61–80.
> <https://doi.org/10.3986/AGS.14021>. Licence CC BY-SA 4.0.

Values were copied as printed (the minus signs are Unicode in the article and ASCII here). Column
names are ours. The paper's reclassification of the Land Use database codes into these classes is its
Table 1, encoded in `reclass.csv`.

`reclass.csv` maps every RABA code to the paper's class. The paper's Table 1 does not list 1310 and
1322, the two meadow codes of the 2002 version (intensive and extensive meadows, per the legend inside
`RABA_2002_SHP.ZIP`); they are mapped to Grasslands here, which is our assumption (recorded as a
deviation). In 2002, code 1500 means "mixed use: agricultural land and forest", not "trees and shrubs";
the paper's Table 1 maps 1500 to Overgrown, and so do we.
