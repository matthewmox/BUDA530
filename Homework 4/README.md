Assignment 4
================

You work for an Ag-Tech consulting firm and were recently promoted when
your former boss (Josh) left for another opportunity. You have taken
over all of your boss’s clients.

One of these clients is a wheat farmer in Manitoba, Canada. Each year,
your team prepares this client a forecast of the number of Growing
Degree Days (GDD) per month for the next year. GDD are a measure of the
amount of warmth that plants have experienced over the past time
calculated by summing the average daily temperature for days where the
avg temp is above a certain threshold (for wheat this is 0 degrees C).
Your client uses this forecast to plan when they plant and harvest their
crops. [More Information About
GDD](https://cropwatch.unl.edu/documents/gdd.pdf).

You’ve had a junior member of your team pull the past 30 years of GDD
data from Gretna, Canada for you using the following code (Note: this
code will only run on GoFirst; A CSV version is included for your
reference).

``` r
library(tidyverse)
```

    ## ── Attaching core tidyverse packages ──────────────────────── tidyverse 2.0.0 ──
    ## ✔ dplyr     1.1.2     ✔ readr     2.1.4
    ## ✔ forcats   1.0.0     ✔ stringr   1.5.0
    ## ✔ ggplot2   3.4.4     ✔ tibble    3.2.1
    ## ✔ lubridate 1.9.3     ✔ tidyr     1.3.0
    ## ✔ purrr     1.0.2     
    ## ── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
    ## ✖ dplyr::filter() masks stats::filter()
    ## ✖ dplyr::lag()    masks stats::lag()
    ## ℹ Use the conflicted package (<http://conflicted.r-lib.org/>) to force all conflicts to become errors

``` r
# Connect to Spark
library(sparklyr)
sc <- spark_connect(master = "local")

# Pull data for station CA005021220
CA005021220<-spark_read_csv(sc,"CA005021220_spark",path="s3a://noaa-ghcn-pds/csv/by_station/CA005021220.csv")

# summarize
GretnaGDD <- CA005021220%>%
  filter(ELEMENT=="TMAX")%>% # get max temp
  select(DATE,TMAX=DATA_VALUE)%>%
  left_join(CA005021220%>% # add in min temp
    filter(ELEMENT=="TMIN")%>%
    select(DATE,TMIN=DATA_VALUE), by="DATE")%>%
  mutate(TMINdeg=TMIN/10,TMAXdeg=TMAX/10)%>% # adjust units from 10th of degrees to degrees
  mutate(YEAR=substr(DATE,1,4),MONTH=substr(DATE,5,6))%>% # create year and month variables
  filter(YEAR>1994)%>% # filter to past 30 years
  select(-TMIN,-TMAX)%>% # remove 10th of degree variables
  mutate(TAVGdeg=(TMINdeg+TMAXdeg)/2)%>% # calculate average temp
  mutate(IsGDD = ifelse(TAVGdeg>0,1,0))%>% # check if average temp is above 0
  mutate(GDD=IsGDD*TAVGdeg)%>% # calculate daily GDD
  group_by(YEAR,MONTH)%>% 
  summarise(GDD=sum(GDD))%>% # aggregate by month and year
  arrange(YEAR,MONTH)%>% # sort data
  collect() # export data to R

# disconnect from Spark
spark_disconnect(sc)
```

Documentation for this data set:

[AWS Listing](https://registry.opendata.aws/noaa-ghcn/)

[AWS README](https://docs.opendata.aws/noaa-ghcn-pds/readme.html)

[GitHub
README](https://github.com/awslabs/open-data-docs/tree/main/docs/noaa/noaa-ghcn)

Josh always insisted that you use a 30-year SMA forecast by month (for
example, to get next March’s forecast, you would take the average of the
past 30 March data points). The client has been complaining for years,
however, that the data is inaccurate in very specific ways (always high
for certain months and low for others). You suspect that is because of a
trend associated with climate change.

Before Josh left, you had raised this idea to him and his solution was
to switch to a 15-year SMA forecast. Both the 30-year and 15-year are
included below.

``` r
library(readr)
GretnaGDD<- read_csv("GretnaGDD.csv")
```

    ## Rows: 349 Columns: 3
    ## ── Column specification ────────────────────────────────────────────────────────
    ## Delimiter: ","
    ## chr (1): MONTH
    ## dbl (2): YEAR, GDD
    ## 
    ## ℹ Use `spec()` to retrieve the full column specification for this data.
    ## ℹ Specify the column types or set `show_col_types = FALSE` to quiet this message.

``` r
GretnaGDD%>%group_by(MONTH)%>%
  summarise(GDDAvg30 = mean(GDD))%>% # get 30-year average by month
  left_join(GretnaGDD%>% # join in 15-year average
              filter(YEAR>2008)%>% # filter to past 15 years
              group_by(MONTH)%>%
              summarise(GDDAvg15 = mean(GDD)), by = "MONTH") # get 15-year average by month
```

    ## # A tibble: 12 × 3
    ##    MONTH GDDAvg30 GDDAvg15
    ##    <chr>    <dbl>    <dbl>
    ##  1 01       0.855    0.741
    ##  2 02       2.01     1.04 
    ##  3 03      26.7     31.9  
    ##  4 04     139.     127.   
    ##  5 05     346.     372.   
    ##  6 06     514.     534.   
    ##  7 07     600.     610.   
    ##  8 08     555.     575.   
    ##  9 09     405.     432.   
    ## 10 10     179.     183.   
    ## 11 11      32.6     36.2  
    ## 12 12       1.74     2.06

You have long thought that Exponential Smoothing or ARIMA would be
better methodologies to use, but Josh always said, “There is no way we
can explain that to the client. Stick to tried and true methods.”

Now that you are in charge, you want to evaluate whether or not these
methods would be better.

1.  Convert the dataframe `GretnaGDD` to a time-series object using the
    `ts` function.

``` r
GretnaTS <- ts(GretnaGDD$GDD,start=c(GretnaGDD$YEAR[1],GretnaGDD$MONTH[1]),frequency = 12)
```

2.  Plot the time series using the `plot.ts` function.

``` r
plot.ts(GretnaTS)
```

![](README_files/figure-gfm/unnamed-chunk-4-1.png)<!-- -->

3.  Fit an Exponential Smoothing model to the data using the `ets`
    function.

``` r
library(forecast)
```

    ## Warning: package 'forecast' was built under R version 4.3.2

    ## Registered S3 method overwritten by 'quantmod':
    ##   method            from
    ##   as.zoo.data.frame zoo

``` r
tsmod1<-ets(GretnaTS)
summary(tsmod1)
```

    ## ETS(A,N,A) 
    ## 
    ## Call:
    ##  ets(y = GretnaTS) 
    ## 
    ##   Smoothing parameters:
    ##     alpha = 0.0881 
    ##     gamma = 1e-04 
    ## 
    ##   Initial states:
    ##     l = 209.0577 
    ##     s = -230.6588 -202.3092 -54.6406 170.6303 321.2735 366.3611
    ##            279.2602 112.7139 -93.6458 -205.0164 -231.3861 -232.5821
    ## 
    ##   sigma:  48.2849
    ## 
    ##      AIC     AICc      BIC 
    ## 4765.360 4766.802 4823.186 
    ## 
    ## Training set error measures:
    ##                    ME     RMSE      MAE MPE MAPE      MASE      ACF1
    ## Training set 1.483018 47.30651 33.18622 NaN  Inf 0.8530739 0.2009029

``` r
plot(tsmod1)
```

![](README_files/figure-gfm/unnamed-chunk-5-1.png)<!-- -->

4.  Fit an ARIMA model to the data using the `auto.arima` function.

``` r
tsmod2<-auto.arima(GretnaTS)
summary(tsmod2)
```

    ## Series: GretnaTS 
    ## ARIMA(0,0,1)(2,1,2)[12] 
    ## 
    ## Coefficients:
    ##          ma1    sar1     sar2     sma1    sma2
    ##       0.2746  0.7525  -0.1179  -1.5601  0.6359
    ## s.e.  0.0557  0.3143   0.0779   0.3105  0.2581
    ## 
    ## sigma^2 = 2307:  log likelihood = -1787.87
    ## AIC=3587.75   AICc=3588   BIC=3610.67
    ## 
    ## Training set error measures:
    ##                   ME     RMSE    MAE MPE MAPE      MASE        ACF1
    ## Training set 6.96577 46.85064 30.716 NaN  Inf 0.7895753 -0.02329668

5.  Forecast both models out 12 months. For example, if one of your
    models was named `mod1` you could forecast out 12 months with the
    code below:

``` r
myforecast<-forecast(tsmod1,h=12)
summary(myforecast)
plot(myforecast)

myforecast2 <- forecast(tsmod2,h=12)
summary(myforecast2)
plot(myforecast2)
```

6.  Since taking over for Josh, you have noticed he was very poor at
    documenting processes. Had you not worked for him previously, you
    would have to completely reinvent the wheel. You don’t want that to
    be the case for whoever takes over your position when you get
    promoted. Create documentation for this analysis. Explain your
    motivation, methodology, and results. The audience of this
    documentation is whoever takes over your position in the future.

### GDD Forecasting

This documentation outlines the process and findings of the annual
forecast of Growing Degree Days (GDD) prepared for wheat farmers. GDD is
a crucial measure in agriculture that helps predict plant growth
patterns based on accumulated warmth.The motivation behind this analysis
stems from the need to assist clients in planning their agricultural
activities efficiently. Understanding GDD trends allows for optimized
planting schedules, irrigation planning, and harvest times, leading to
improved crop yields and resource management. [More Information About
GDD](https://cropwatch.unl.edu/documents/gdd.pdf)

Methodology:

Our methodology employs the sparklyr package to interface with a Spark
session, enabling the processing of large-scale weather datasets to
compute GDD for a targeted location across a specific timeframe. Here’s
a breakdown of the process:

Spark Setup: Utilize sparklyr to establish a connection to Apache Spark,
using spark_connect with the master node set to “local”. This
configuration is ideal for either development purposes or small-scale
analyses. Data Acquisition: Weather station data, identified by “X”, is
imported into a Spark DataFrame using spark_read_csv, from a chosen S3
bucket. Data Preprocessing: Apply SQL queries to organize the dataset by
YEAR and MONTH, calculating the total GDD for each period to obtain
monthly summaries.

[AWS Listing](https://registry.opendata.aws/noaa-ghcn/)

[AWS README](https://docs.opendata.aws/noaa-ghcn-pds/readme.html)

[GitHub
README](https://github.com/awslabs/open-data-docs/tree/main/docs/noaa/noaa-ghcn)

Processing and Analysis

The data analysis involves several key steps to transform GDD data into
actionable insights:

1.  Time-Series Conversion: Transform the DataFrame into a time-series
    object to facilitate temporal analyses.
2.  Visualization: Generate time-series plots to visualize GDD trends
    over the defined period.
3.  Model Application: Implement Exponential Smoothing and ARIMA models
    to fit the GDD data accurately.
4.  Forecasting: Use both models to forecast future GDD values,
    providing valuable predictive insights.

Conclusion:

This guide outlines the essential steps for converting GDD data into a
time-series format, enabling effective visualization, model application,
and forecasting. By analyzing GDD patterns, wheat farmers can make
informed decisions, enhancing their agricultural planning and
operations. Our methodology, leveraging powerful data processing and
analytical techniques, aims to offer farmers predictive insights for
better crop management and yield optimization.

7.  Pick a forecasting methodology to present to the client and explain
    your decision. As above, the audience is whoever takes over your
    position in the future. You should weigh the pros and cons of each
    approach (30-year, 15-year, ETS, and ARIMA) including a cost/
    benefits analysis of what information each methodology adds vs how
    easy it is to explain to the client. Note: there is no right or
    wrong answer here, you will be graded on how you explain your
    decision, not on the decision itself.

When tasked with selecting the most suitable forecasting methodology for
our client, it is imperative to strike an optimal balance among several
critical factors: forecast accuracy, the simplicity of explanation to
non-specialists, and the relevance of the data used to current trends
and practices. After careful consideration of the available
options—including 30-year and 15-year historical data analyses,
Exponential Smoothing (ETS), and the Autoregressive Integrated Moving
Average (ARIMA) model—I recommend adopting the ARIMA model based on a
15-year historical data set. This recommendation is grounded in the
following analysis:

Accuracy The ARIMA model stands out for its robust predictive
capabilities, as evidenced by superior performance metrics such as lower
Akaike Information Criterion (AIC) scores and reduced error measures
compared to alternative models. This enhanced accuracy is crucial for
providing reliable forecasts that the client can confidently incorporate
into their planning and decision-making processes.

Relevance A 15-year historical data perspective is chosen over a 30-year
span for several reasons. Firstly, it more accurately reflects recent
climatic changes and their impact on agricultural cycles, making the
insights gleaned significantly more pertinent to the client’s immediate
needs. Secondly, it captures shifts in agricultural practices and
technological advancements, ensuring the forecasts are grounded in the
current agricultural context.

Cost-Benefit Analysis 30-Year Data Analysis: Offers a long-term
perspective but may dilute recent trends and shifts in practices,
potentially reducing its immediate applicability. 15-Year Data Analysis:
Provides a balance, capturing recent trends and changes in agriculture
without overwhelming the model with outdated information. ETS
(Exponential Smoothing): While simpler to explain and understand, ETS
may not capture the complexity of agricultural data as effectively as
ARIMA, potentially leading to less accurate forecasts. ARIMA: Though
more complex and potentially challenging to explain to a lay audience,
its predictive accuracy and adaptability to non-linear trends offer
significant benefits. This complexity is deemed a worthwhile trade-off
for the gains in forecast reliability and relevance.

Decision Rationale The choice of ARIMA with 15-year data is a strategic
one, acknowledging the inherent trade-offs between model complexity and
forecasting efficacy. This approach is favored for its potential to
deliver actionable, accurate forecasts that reflect recent trends and
shifts in agricultural practice. The decision assumes that the
investment in explaining the model’s complexity to the client is
justified by the substantial benefits of enhanced forecast accuracy and
the resulting improvements in planning and decision-making capabilities.

8.  Regardless of your answer for the previous question, now suppose you
    decided to move forward with Exponential Smoothing. Write a memo for
    your client explaining this switch. Your client is a farmer; they
    have some college education and understand agriculture extremely
    well but stats isn’t their forte. Despite your misgivings about
    Josh’s methodology, you do know that he was correct about the client
    liking that they understood SMA. You know there will be some
    resistance to switching to this new methodology. Keep this in mind
    as you explain. Also explain the confidence intervals and how they
    can help the client with decision making.

Dear Ricky,

I am contacting you to discuss an important improvement to our
forecasting methodology, which we believe will greatly benefit your
agricultural planning and decision-making processes. To provide you with
the most accurate and useful forecasts for Growing Degree Days (GDD), we
are introducing Exponential Smoothing (ETS) as our new forecasting
methodology. This approach builds on the simplicity and intuitive nature
of the Simple Moving Average (SMA) method that you are already familiar
with. ETS incorporates improvements to better capture and predict the
seasonal patterns that are crucial for agricultural success.

Why Exponential Smoothing?

Simplicity and Intuitiveness: ETS is a natural progression from SMA,
offering a straightforward way to account for trends and seasonality in
temperature data. It adjusts more dynamically to recent changes,
ensuring that our forecasts remain as relevant and accurate as possible.

Enhanced Accuracy: While maintaining an approachable framework, ETS
introduces a refined way to analyze data and allows for a more accurate
prediction of future conditions, which is vital for planning planting,
irrigation, and harvesting.

Confidence Intervals for Decision Making:

What Are Confidence Intervals? These intervals provide a range of values
within which we expect the actual GDD values to fall, with a certain
level of confidence (typically 95%). They offer a visual and statistical
way to understand the potential variability in our forecasts.

How Can They Help You? Confidence intervals allow for better risk
management by showing the possible upper and lower bounds of the GDD
forecast. For instance, a wider interval suggests greater uncertainty,
signaling a need for more cautious planning.

We understand that transitioning to a new methodology may come with
reservations. Our goal is to ensure that you feel confident and informed
about how ETS works and why it’s beneficial for your farm’s planning and
operations. To achieve this goal, we will provide detailed explanations,
training sessions if necessary, and ongoing support to ensure a smooth
transition.

Thank you for entrusting us with your business. We are committed to
leveraging the best available methods to support your farming
activities, and we believe that ETS is a step forward in achieving more
reliable and actionable forecasts for your farm.

Best regards, Matthew Moxam

9.  In the previous question do you think a memo is the best way to
    explain this to your client? If yes, explain why. If no, explain
    what other methodology you would use (phone call, in-person
    presentation, etc.) and why.

A GitHub README.md is an excellent tool for project documentation. It
combines accessibility and flexibility into a single, effective
communication platform. Markdown formatting enhances the utility of this
documentation tool, allowing for a range of formatting options such as
text styling, embedding images and links. This enables the creation of
informative and engaging documents. It is particularly helpful when
explaining complex concepts or methodologies, as it allows for the
inclusion of visual aids, code snippets, and external resources to aid
comprehension. Interactive examples and demonstrations linked within a
README.md provide tangible insights into the practical application of
documented methodologies.

In summary, a GitHub README.md file is an ideal blend of visibility,
clarity, and interactivity for project documentation. It is especially
helpful for documenting technical methodologies like Exponential
Smoothing. Its ability to concisely convey complex information while
supporting engagement makes it an unparalleled resource in the realm of
project communication.

Should there be any difficulty in grasping the documented concepts, we
should schedule a detailed discussion to navigate through the
complexities together.

10. Your client was impressed with your analysis and has started
    referring you to their friends. One of those friends - a corn farmer
    in Omaha, Nebraska, USA - has hired you to forecast GDD for them.
    You have tasked a junior analyst with pulling a report for you in
    Spark (using the code above as a reference) and they have sent you
    the following email:

“Hey Boss,

I started trying to change Josh’s old Spark code to pull the GDD report
for Omaha and ran into some issues I could use your help with:

1.  I looked it up and the GDD threshold for corn is 10 degrees C,
    not 0. Do you know where I should change the code for this?
2.  I looked up the stations for Omaha in that document you told me
    about [Stations
    Document](https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt).
    There are a ton of options… I tried a couple and so far I’m either
    not getting back any results or not getting a full 30 years worth of
    data. Any idea what I should do about this?

Thanks, Junior”

You weren’t around when Josh wrote this code for Manitoba, but you do
remember him talking about it. Specifically you remember him mentioning
that (1) not all stations collect all data types (for instance some only
collect rain), (2) stations are created and shut down all the time but
are all still in the data bucket (i.e. there may be station options that
haven’t existed very long, or that have shut down years ago), (3) that
he actually had to use a station close to the Manitoba client but not in
the exact same city to get the data he needed, (3) that there was a
period of time he actually had to use data from 2 stations to get the
data he needed, and (4) that he wrote a loop to produce a summary table
for each station in the area and then looked at the results to make a
decision on what station to use. Given this information, write a
response to the junior analyst’s email (you do not need to write or run
any code for this). Include links to resources you think may be helpful.

Hi Junior,

Great to hear from you and see your progress on adapting the Spark code
for the GDD report specific to corn farming in Omaha. Let’s address each
of your concerns:

1.  Adjusting GDD Threshold for Corn

For corn, the GDD calculation starts from a base temperature of 10
degrees C, not 0. In the Spark code where we calculate the daily GDD,
you’ll find a line similar to this:

mutate(IsGDD = ifelse(TAVGdeg\>0,1,0))%\>% \# check if average temp is
above 0

This line of code is a conditional check to identify if the average
temperature is above the threshold to contribute to GDD. Currently, it’s
set for 0 degrees. You’ll adjust it to 10 degrees C. So, you’d modify
the line that calculates IsGDD to check against 10 degrees C instead of
0. This means if TAVGdeg \> 10, then it contributes to GDD.

2.  Selecting the Correct Weather Station: Selecting a weather station
    with a comprehensive data set covering the desired 30-year span can
    be challenging due to the variability in data availability across
    stations. Here are a few steps to refine your search and selection
    process:

Filter by Proximity and Data Completeness: Prioritize stations that are
closest to Omaha and have a record of consistent data reporting over the
years. The ghcnd-stations.txt file includes metadata such as the
latitude and longitude that can help you identify stations in or near
Omaha.

Verify Data Availability: Once you’ve identified potential stations, use
the GHCN (Global Historical Climatology Network) database to check the
extent of the data each station has. You’re looking for stations with a
near-complete dataset over the last 30 years. If you’re still
encountering issues with data completeness, consider aggregating data
from multiple stations within a reasonable distance of Omaha to
compensate for gaps. However, this approach requires careful
consideration to ensure the aggregated data accurately represents the
area’s climate.

Here’s a snippet to help you filter stations based on proximity (you’ll
need to adjust the lat-long parameters for Omaha): Omaha_stations \<-
stations\[stations$lat >= [MIN_LAT] & stations$lat \<= \[MAX_LAT\] &
stations$long >= [MIN_LONG] & stations$long \<= \[MAX_LONG\],\]

This code can also help you find the data you need even if a station
doesn’t collect the necessary data.

Remember, the key to selecting a station is balancing between
geographical proximity and data completeness. It might take a few
attempts to find the optimal station.

Keep up the good work, and don’t hesitate to reach out if you hit any
more roadblocks or need further clarification.

Best, Matthew

11. Outside of this hypothetical case study, this particular problem
    matters. The [US Climate
    Normals](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals)
    is essentially a 30-year SMA by day released by NOAA every year. It
    is used in a wide range of industries (industrial planning, HVAC,
    etc.). Recently, due to climate change, NOAA has had to start
    releasing a 15-year version of the climate normals. Read the article
    [Why are the new climate normals
    abnormal?](https://iee.psu.edu/news/blog/why-are-new-climate-normals-abnormal).
    Answering now as yourself (i.e. a citizen of the world) what are
    your thoughts about this? Do you think NOAA should investigate using
    methods that pick up on trend for climate normals (i.e. Exponential
    Smoothing)? Keep in mind, NOAA does not currently represent this
    data set as a “forecast” but rather as a benchmark of typical
    climate conditions. If they were going to use one of these
    methodologies, should they consider branding it differently? How
    should they handle imputation of missing values (this is fairly easy
    for SMA but not so easy for ES)?

As a citizen of the world observing the impacts of climate change unfold
in real-time, I find the rapid change worrisome to say the least.In
Wyoming, where I live, the concern is palpable, especially with the
recent trend of unusually high winter temperatures. These conditions not
only disrupt the natural rhythm of seasons but also heighten the risk of
avalanches due to the altered formation of ice layers. The shift by NOAA
to release a 15-year version of the climate normals, in addition to the
traditional 30-year Simple Moving Average (SMA), is a significant
acknowledgment of the rapid changes our climate is undergoing. The
adaptation reflects the necessity to provide more relevant and current
benchmarks that can better guide industries affected by climate
variability, from agriculture to energy management.The idea of NOAA
exploring methods like Exponential Smoothing (ES) for analyzing climate
normals is intriguing. Unlike SMA, which gives equal weight to all
observations in the period, ES can emphasize more recent data,
potentially offering a more responsive and accurate reflection of
current climate trends. Given the rapid pace of climate change,
methodologies that can pick up on and adjust to trends could provide
more useful benchmarks for industries to navigate the changing climate
landscape.

If NOAA were to use trend-based methods for climate normals, it would
indeed necessitate a different branding or communication strategy. It’s
crucial to distinguish these from traditional climate normals to avoid
confusion. This distinction would help users understand that these
figures incorporate more than just an average but also account for
recent trends and changes. Introducing methods like ES, which are
inherently more predictive, might blur the lines bewtweeen benchmarks
and forecasting. NOAA would need to carefully communicate the purpose of
these new normals, emphasizing their role as trend-adjusted forecasts to
assist in planning and decision-making.

The challenge of imputing missing values in ES is indeed more complex
than in SMA. NOAA would need to adopt sophisticated imputation methods
that maintain the integrity of the data while accurately reflecting
recent trends. Techniques such as interpolation, regression imputation,
or even machine learning models could be considered, depending on the
nature and extent of the missing data. The chosen method would need to
be transparent and justifiable to maintain the credibility and utility
of the climate normals.

[Bridger Teton Avalanche
Center](https://bridgertetonavalanchecenter.org/observations/#/view/avalanches)

[Avalanche Accidents](https://bridgertetonavalanchecenter.org/wyoming-fatalities-by-date-list/)
