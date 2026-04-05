using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using BayatGames.SaveGameFree;
using ChartUtil.Demo;
using TMPro;
using LightShaft.Scripts;

public class StatsControllerExpanded : MonoBehaviour
{
    public static StatsControllerExpanded Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    float avgGeneric = 1.3f;
    float avgPersonTotal = 8f;
    float avgPersonNumber;
    float avgPersonColor;
    float avgPersonShape;
    float avgPersonWord;
    float avgPersonBeat;
    float avgPersonMemory;
    float avgPersonMotor;

    float stdGeneric = 1.6f;
    float stdPersonTotal = 0.025f;
    float stdPersonNumber;
    float stdPersonColor;
    float stdPersonShape;
    float stdPersonWord;
    float stdPersonBeat;
    float stdPersonMemory;
    float stdPersonMotor;

    public float numberOfMerges = 0f;
    public string currentPlotShown;
    TextMeshProUGUI textCurrentPlotShown;
    TextMeshProUGUI textNextButton;
    TextMeshProUGUI textPrevButton;
    TextMeshProUGUI rankingValue;
    TextMeshProUGUI rankingText;

    VideoObject videoObject;
    YoutubePlayer youtubePlayer;
    MusicPlayer musicPlayer;

    public int numberOfGamesPlayed = 0;
    float numberGainAvg = 0;
    float colorGainAvg = 0;
    float shapeGainAvg = 0;
    float wordGainAvg = 0;
    float beatGainAvg = 0;
    float memoryGainAvg = 0;
    float motorGainAvg = 0;

    Dictionary<string, List<float>> statsDictionary = new Dictionary<string, List<float>>();
    Dictionary<string, float> dataCurrentGame = new Dictionary<string, float>();

    public List<float> listMean = new List<float>();
    public List<float> listStd = new List<float>();

    public static ChartUtil.Chart chartStats;
    public static ChartUtil.Chart chartDistribution;
    public static ChartUtil.Chart chartRanking;
    public static ChartUtil.ChartData chartData;
    public static ChartUtil.ChartData chartDistributionData;
    public static ChartUtil.ChartData chartRankingData;

    ChartUtil.Series distributionNumberSeries = new ChartUtil.Series();
    ChartUtil.Series distributionColorSeries = new ChartUtil.Series();
    ChartUtil.Series distributionShapeSeries = new ChartUtil.Series();
    ChartUtil.Series distributionWordSeries = new ChartUtil.Series();
    ChartUtil.Series distributionBeatSeries = new ChartUtil.Series();
    ChartUtil.Series distributionMemorySeries = new ChartUtil.Series();
    ChartUtil.Series distributionMotorSeries = new ChartUtil.Series();
    ChartUtil.Series rankingSeries = new ChartUtil.Series();

    static List<string> chartLineTypes = new List<string> { "Mana", "Mana Speed",
        "Math", "Visual", "Spatial", "Verbal", "Music", "Memory", "Motor",
        "Math: Add", "Math: Multiply", "Math: Coprimes",
        "Math: Vector", "Math: Interval", "Math: Trigonometry", "Math: Sort",
        "Visual: Add", "Visual: Subtract",
        "Visual: Gray", "Visual: Text"  , "Spatial: Triangle", "Spatial: Rectangle",
        "Spatial: 3 Shapes", "Spatial: Kanizsa", "Spatial: Angle",
        "Spatial: Hanoi", "Verbal: Antonym Verbs", "Verbal: Antonym Adjectives",
        "Verbal: Antonym Nouns", "Verbal: Synonym Verbs", "Verbal: Synonym Adjectives",
        "Verbal: Grammar", "Verbal: Question Answer", "Verbal: Generate Words",
        "Music: Double Slow", "Music: Single Slow",
        "Music: Double Fast", "Music: Single Fast", "Music: Tik and Tok",
        "Music: 5 Slots", "Memory: Easy", "Memory: Moderate", "Memory: Hard",
        "Physical: Fast and Accurate" ,
        "Physical: Visit the Bank", "Physical: Visit All Slots" };

    static List<string> chartDistributionCategories = new List<string> { "Math", "Visual", "Spatial", "Verbal" , "Music", "Memory", "Physical"};
    static List<string> chartRankingCategories = new List<string> { "Overall", "Math", "Visual", "Spatial", "Verbal", "Music", "Memory", "Physical" };

    ResetDialogCanvas resetDialogCanvas;

    void Start()
    {
        //ResetAllStats();

        PrepareMeanAndStd();

        foreach (string lineChartName in chartLineTypes)
        {
            if (dataCurrentGame.ContainsKey(lineChartName) == false)
            {
                dataCurrentGame.Add(lineChartName, 0f);
            }

        }

        videoObject = FindAnyObjectByType<VideoObject>();
        if (videoObject != null)
        {
            youtubePlayer = videoObject.GetComponentInChildren<YoutubePlayer>();
            videoObject.gameObject.SetActive(false);
        }
        
        resetDialogCanvas = FindAnyObjectByType<ResetDialogCanvas>();

        CurrentPlotShownText currentPlotShownText = FindAnyObjectByType<CurrentPlotShownText>();
        if(currentPlotShownText != null)
        {
            textCurrentPlotShown = currentPlotShownText.GetComponent<TextMeshProUGUI>();
        }

        RankingValueStats rankingValueStats = FindAnyObjectByType<RankingValueStats>();
        if(rankingValueStats != null)
        {
            rankingValue = rankingValueStats.GetComponent<TextMeshProUGUI>();
        }

        TextMeshProUGUI[] textUIs = FindObjectsByType<TextMeshProUGUI>(FindObjectsSortMode.None);
        foreach(TextMeshProUGUI itemIter in textUIs)
        {
            if(itemIter.gameObject.name == "Next Button")
            {
                textNextButton = itemIter;
            }
            if (itemIter.gameObject.name == "Previous Button")
            {
                textPrevButton = itemIter;
            }
            if (itemIter.gameObject.name == "Ranking Text")
            {
                rankingText = itemIter;
            }
        }

        
        if (resetDialogCanvas)
        {
            resetDialogCanvas.gameObject.SetActive(false);
        }

        LoadSavedStats();

        // Graph/Chart Init
        ChartUtil.Chart[] chartsAll = FindObjectsByType<ChartUtil.Chart>(FindObjectsSortMode.None);
        foreach (ChartUtil.Chart chartIter in chartsAll)
        {
            if (chartIter.gameObject.name == "Chart Line")
            {
                chartStats = chartIter;
                chartData = chartStats.GetComponentInParent<ChartUtil.ChartData>();
                chartData.series = new List<ChartUtil.Series>();

                foreach (string lineChartName in chartLineTypes)
                {
                    PrepareLineChartData(lineChartName);
                }
            }
            else if (chartIter.gameObject.name == "Chart Distribution")
            {
                chartDistribution = chartIter;
                chartDistributionData = chartDistribution.GetComponentInParent<ChartUtil.ChartData>();
                chartDistributionData.series = new List<ChartUtil.Series>();
                PrepareDistributionData();
            }
            else if (chartIter.gameObject.name == "Chart Ranking")
            {
                chartRanking = chartIter;
                chartRankingData = chartRanking.GetComponentInParent<ChartUtil.ChartData>();
                chartRankingData.series = new List<ChartUtil.Series>();
                PrepareRankingData();
            }
        }

    }

    public void PlayVideo(string videoURL)
    {
        musicPlayer = MusicPlayer.Instance;
        if (musicPlayer != null)
        {
            musicPlayer.SetVolume(0f);
        }

        if (videoObject != null)
        {
            videoObject.gameObject.SetActive(true);
            if (youtubePlayer != null)
            {
                youtubePlayer.Play(videoURL);
            }
        }
       

    }

    public void HideVideo()
    {
        if (videoObject != null)
        {
            videoObject.gameObject.SetActive(false);
        }
 
        musicPlayer = MusicPlayer.Instance;
        if (musicPlayer != null)
        {
            musicPlayer.SetVolume(PlayerPrefsController.GetMasterVolume());
        }
    }

    public float GetAvgGeneric()
    {
        return avgGeneric;
    }

    public float GetStdGeneric()
    {
        return stdGeneric;
    }


    private void PrepareMeanAndStd()
    {
        //Mean and Std
        for (int i = 0; i < chartLineTypes.Count; ++i)
        {
            if (i == 0)
            {
                listMean.Add(2000f);
            }
            else if (i == 1)
            {
                listMean.Add(12f);
            }
            else if (i == 2)
            {
                avgPersonNumber = avgGeneric * 0.96f;
                listMean.Add(avgPersonNumber);
            }
            else if (i == 3)
            {
                avgPersonColor = avgGeneric * 0.99f;
                listMean.Add(avgPersonColor);
            }
            else if (i == 4)
            {
                avgPersonShape = avgGeneric * 0.95f;
                listMean.Add(avgPersonShape);
            }
            else if (i == 5)
            {
                avgPersonWord = avgGeneric * 0.78f;
                listMean.Add(avgPersonWord);
            }
            else if (i == 6)
            {
                avgPersonBeat = avgGeneric * 0.95f;
                listMean.Add(avgPersonBeat);
            }
            else if (i == 7)
            {
                avgPersonMemory = avgGeneric * 0.9f;
                listMean.Add(avgPersonMemory);
            }
            else if (i == 8)
            {
                avgPersonMotor = avgGeneric * 0.93f;
                listMean.Add(avgPersonMotor);
            }
            else if (i == 13 || i == 14 || i == 24 || i == 25 || i == 26
                || i == 27 || i == 28 || i == 37
                || i == 42 || i == 45)
            {
                listMean.Add(avgGeneric * 0.85f);
            }
            else if (i == 36 || i == 19)
            {
                listMean.Add(avgGeneric * 0.9f);
            }
            else if (i == 39)
            {
                listMean.Add(avgGeneric * 0.8f);
            }
            else if (i == 29 || i == 30 || i == 31 || i == 32)
            {
                listMean.Add(avgGeneric * 0.75f);
            }
            else if (i == 33)
            {
                listMean.Add(avgGeneric * 0.6f);
            }
            else if(i == 20 || i == 21 || i == 22 || i == 23 || i == 38)
            {
                listMean.Add(avgGeneric * 0.92f);
            }
            else
            {
                listMean.Add(avgGeneric);
            }

        }

        for (int i = 0; i < chartLineTypes.Count; ++i)
        {
            if (i == 0)
            {
                listStd.Add(0.002f);
            }
            else if (i == 1)
            {
                listStd.Add(0.2f);
            }
            else
            {
                listStd.Add(stdGeneric);
            }
            stdPersonTotal = stdGeneric / 70;
            stdPersonNumber = stdGeneric;
            stdPersonColor = stdGeneric;
            stdPersonShape = stdGeneric;
            stdPersonWord = stdGeneric;
            stdPersonBeat = stdGeneric;
            stdPersonMemory = stdGeneric;
            stdPersonMotor = stdGeneric;

        }
    }

    private void FlushStatsDictionary()
    {
        statsDictionary = new Dictionary<string, List<float>>();
        foreach (string lineChartName in chartLineTypes)
        {
            statsDictionary.Add(lineChartName, new List<float>());
        }

        PrepareMeanAndStd();
        statsDictionary.Add("MeanGross", listMean);
        statsDictionary.Add("StdGross", listStd);

        SaveGame.Save<Dictionary<string, List<float>>>("statsDictionary", statsDictionary);
    }

    private void LoadSavedStats()
    {
        if (SaveGame.Exists("statsDictionary"))
        {
            statsDictionary = SaveGame.Load<Dictionary<string, List<float>>>("statsDictionary");
        }
        else
        {
            FlushStatsDictionary();
        }
    }

    public void UpdateNumberOfMerges(float noMergeUpdate)
    {
        numberOfMerges = noMergeUpdate;
    }

    public void UpdateDataGeneric(string dataName, float dataValue)
    {
        if(dataValue != -1000f && dataName != "Mana" && dataName != "Mana Speed")
        {
            dataCurrentGame[dataName] = dataValue / (numberOfMerges + 1f);
        }
        else
        {
            dataCurrentGame[dataName] = dataValue;
        }
        
    }

    public void SaveGameStats()
    {
        foreach (string lineChartName in chartLineTypes)
        {
            if(dataCurrentGame[lineChartName] != -1000f)
            {
                statsDictionary[lineChartName].Add(dataCurrentGame[lineChartName]);
            }
        }

        SaveGame.Save<Dictionary<string, List<float>>>("statsDictionary", statsDictionary);

    }

    public void FlushCurrentGameData()
    {
        if (dataCurrentGame.ContainsKey("Physical: Visit All Slots") == false)
        {
            foreach (string lineChartName in chartLineTypes)
            {
                if (dataCurrentGame.ContainsKey(lineChartName) == false)
                {
                    dataCurrentGame.Add(lineChartName, 0f);
                }
                    
            }
        }
        else
        {
            foreach (string lineChartName in chartLineTypes)
            {
                if (dataCurrentGame.ContainsKey(lineChartName) == true)
                {
                    dataCurrentGame[lineChartName] = 0f;
                }
                    
            }
        }

    }

    public void PrepareLineChartData(string chartName)
    {
        float percentileMult = 100f;
        if (chartName == "Mana" || chartName == "Mana Speed")
        {
            percentileMult = 1f;
        }
        ChartUtil.Series chartSeries = new ChartUtil.Series();
        chartSeries.name = chartName;
        List<float> dataList = statsDictionary[chartName];
        //Debug.Log(chartName);
        foreach (float dataPoint in dataList)
        {
            //Debug.Log(dataPoint);
            chartSeries.data.Add(new ChartUtil.Data(Mathf.Round(percentileMult * dataPoint)));
        }

        chartData.series.Add(chartSeries);

    }

    public float ApplyLogistic(float GainPerson, float GainMean, float GainStd, float nonlinearityProb = 1f)
    {
        float returnVal = Mathf.Round(100f / (1f + Mathf.Exp(-GainStd * (GainPerson - GainMean))));
        returnVal = Mathf.Max(returnVal, 6f);
        returnVal = Mathf.Pow(returnVal, nonlinearityProb);
        return returnVal;
    }

    private float ComputeAverageList(List<float> listData)
    {
        float sumList = 0f;
        foreach(float itemList in listData)
        {
            sumList += itemList;
        }
        return sumList / (listData.Count + 0.001f);
    }

    private float ComputeMaxList(List<float> listData)
    {
        float maxList = -1000f;
        foreach (float itemList in listData)
        {
            if(itemList > maxList)
            {
                maxList = itemList;
            }
        }
        return maxList;
    }

    private void PrepareAverageData()
    {
        numberGainAvg = ComputeAverageList(statsDictionary["Math"]);
        colorGainAvg = ComputeAverageList(statsDictionary["Visual"]);
        shapeGainAvg = ComputeAverageList(statsDictionary["Spatial"]);
        wordGainAvg = ComputeAverageList(statsDictionary["Verbal"]);
        beatGainAvg = ComputeAverageList(statsDictionary["Music"]);
        memoryGainAvg = ComputeAverageList(statsDictionary["Memory"]);
        motorGainAvg = ComputeAverageList(statsDictionary["Motor"]);
    }

    public void PrepareDistributionData()
    {
        PrepareAverageData();
        float nonlinearityProb = 2f;
        float totalValue = (ApplyLogistic(numberGainAvg, avgPersonNumber, stdPersonNumber, nonlinearityProb) +
            ApplyLogistic(colorGainAvg, avgPersonColor, stdPersonColor, nonlinearityProb) +
            ApplyLogistic(shapeGainAvg, avgPersonShape, stdPersonShape, nonlinearityProb) +
            ApplyLogistic(wordGainAvg, avgPersonWord, stdPersonWord, nonlinearityProb) +
            ApplyLogistic(beatGainAvg, avgPersonBeat, stdPersonBeat, nonlinearityProb) +
            ApplyLogistic(memoryGainAvg, avgPersonMemory, stdPersonMemory, nonlinearityProb) +
            ApplyLogistic(motorGainAvg, avgPersonMotor, stdPersonMotor)) + 0.0001f;
        distributionNumberSeries.name = "Math";
        distributionNumberSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(numberGainAvg, avgPersonNumber, stdPersonNumber, nonlinearityProb) / totalValue)));
        distributionColorSeries.name = "Visual";
        distributionColorSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(colorGainAvg, avgPersonColor, stdPersonColor, nonlinearityProb) / totalValue)));
        distributionShapeSeries.name = "Spatial";
        distributionShapeSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(shapeGainAvg, avgPersonShape, stdPersonShape, nonlinearityProb) / totalValue)));
        distributionWordSeries.name = "Verbal";
        distributionWordSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(wordGainAvg, avgPersonWord, stdPersonWord, nonlinearityProb) / totalValue)));
        distributionBeatSeries.name = "Music";
        distributionBeatSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(beatGainAvg, avgPersonBeat, stdPersonBeat, nonlinearityProb) / totalValue)));
        distributionMemorySeries.name = "Memory";
        distributionMemorySeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(memoryGainAvg, avgPersonMemory, stdPersonMemory, nonlinearityProb) / totalValue)));
        distributionMotorSeries.name = "Physical";
        distributionMotorSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(motorGainAvg, avgPersonMotor, stdPersonMotor, nonlinearityProb) / totalValue)));

        chartDistributionData.categories = chartDistributionCategories;

        chartDistributionData.series.Add(distributionNumberSeries);
        chartDistributionData.series.Add(distributionColorSeries);
        chartDistributionData.series.Add(distributionShapeSeries);
        chartDistributionData.series.Add(distributionWordSeries);
        chartDistributionData.series.Add(distributionBeatSeries);
        chartDistributionData.series.Add(distributionMemorySeries);
        chartDistributionData.series.Add(distributionMotorSeries);

    }

    public void PrepareRankingData()
    {
        PrepareAverageData();
        float totalValue = numberGainAvg + colorGainAvg + shapeGainAvg + wordGainAvg + beatGainAvg + memoryGainAvg + motorGainAvg;
        
        rankingSeries.name = "Ranking";
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(totalValue, avgPersonTotal, stdPersonTotal) -1f )); 
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(numberGainAvg, avgPersonNumber, stdPersonNumber) -1f ));
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(colorGainAvg, avgPersonColor, stdPersonColor) -1f ));
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(shapeGainAvg, avgPersonShape, stdPersonShape) -1f));
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(wordGainAvg, avgPersonWord, stdPersonWord) -1f));
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(beatGainAvg, avgPersonBeat, stdPersonBeat) -1f));
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(memoryGainAvg, avgPersonMemory, stdPersonMemory) -1f));
        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(motorGainAvg, avgPersonMotor, stdPersonMotor) -1f));

        chartRankingData.categories = chartRankingCategories;
        chartRankingData.series.Add(rankingSeries);
    }

    private float GetRankingForGame(string chartName)
    {
        List<float> listMeanStd = new List<float> { 1.5f, 1f };

        float rankingValue;
        float meanPlayer;
        float maxPlayer;
        float hybridSuccessPlayer;
        List<float> dataList = statsDictionary[chartName];

        if (dataList.Count > 0)
        {
            meanPlayer = ComputeAverageList(dataList);
            maxPlayer = ComputeMaxList(dataList);
            hybridSuccessPlayer = 0.2f * maxPlayer + 0.8f * meanPlayer;
            int index = chartLineTypes.FindIndex(a => a.Contains(chartName));
            rankingValue = ApplyLogistic(hybridSuccessPlayer,
                listMean[index], listStd[index]) - 1f;
        }
        else
        {
            rankingValue = 0f;
        }

        return rankingValue;
    }

    public void ShowLinePlot(string chartName)
    {
        string chartNameShow;
        if (chartName == "Motor")
        {
            chartNameShow = "Physical";
        }
        else
        {
            chartNameShow = chartName;
        }

        currentPlotShown = chartName;
        textCurrentPlotShown.gameObject.SetActive(true);
        textNextButton.gameObject.SetActive(true);
        textPrevButton.gameObject.SetActive(true);
        textCurrentPlotShown.text = chartNameShow;
        rankingText.gameObject.SetActive(true);
        rankingValue.gameObject.SetActive(true);
        float rankingValueChart = GetRankingForGame(chartName);
        rankingValue.text = rankingValueChart.ToString() + "%";
        if (statsDictionary[chartName].Count > 0)
        {
            chartStats.gameObject.SetActive(true);
            chartDistribution.gameObject.SetActive(false);
            chartRanking.gameObject.SetActive(false);
            foreach (var seriesChart in chartData.series)
            {
                if (seriesChart.name == chartName)
                {
                    List<float> dataList = statsDictionary[chartName];
                    List<string> chartValuesXaxis = new List<string>();
                    int time_pt = 0;
                    for (int i = 0; i <= dataList.Count - 1; i++)
                    {
                        time_pt = i + 1;
                        chartValuesXaxis.Add(time_pt.ToString());
                    }
                   
                    chartData.categories = chartValuesXaxis;
                    seriesChart.show = true;

                }
                else
                {
                    seriesChart.show = false;
                }

            }

            chartStats.UpdateChart();   
        }
        else
        {
            chartStats.gameObject.SetActive(false);
            chartDistribution.gameObject.SetActive(false);
            chartRanking.gameObject.SetActive(false);
        }

    }

    public void ShowDistributionPlot()
    {
        currentPlotShown = "Distribution";
        textCurrentPlotShown.gameObject.SetActive(false);
        textNextButton.gameObject.SetActive(false);
        textPrevButton.gameObject.SetActive(false);
        rankingText.gameObject.SetActive(false);
        rankingValue.gameObject.SetActive(false);

        if (statsDictionary["Mana"].Count > 0)
        {
            chartStats.gameObject.SetActive(false);
            chartDistribution.gameObject.SetActive(true);
            chartRanking.gameObject.SetActive(false);
            foreach (var seriesChart in chartDistributionData.series)
            {
                seriesChart.show = true;
            }

            //update chart
            chartDistribution.UpdateChart();
        }
        
    }

    public void ShowRankingPlot()
    {
        currentPlotShown = "Ranking";
        textCurrentPlotShown.gameObject.SetActive(false);
        textNextButton.gameObject.SetActive(false);
        textPrevButton.gameObject.SetActive(false);
        rankingText.gameObject.SetActive(false);
        rankingValue.gameObject.SetActive(false);
        if (statsDictionary["Mana"].Count > 0)
        {
            chartStats.gameObject.SetActive(false);
            chartDistribution.gameObject.SetActive(false);
            chartRanking.gameObject.SetActive(true);
            foreach (var seriesChart in chartRankingData.series)
            {
                seriesChart.show = true;
            }

            //update chart
            chartRanking.UpdateChart();
        }
        
    }

    public void ResetAllStats()
    {
        SaveGame.Delete("statsDictionary");
        numberOfGamesPlayed = 0;
        HideResetDialog();
        FlushStatsDictionary();
        Start();
        ShowNextLinePlot();
    }

    public void ShowResetDialog()
    {
        resetDialogCanvas.gameObject.SetActive(true);
        resetDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(true);
    }

    public void HideResetDialog()
    {
        resetDialogCanvas.gameObject.SetActive(false);
        resetDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(false);
    }


    public void ShowNextLinePlot()
    {
        //Mana group
        if (currentPlotShown == "Mana")
        {
            ShowLinePlot("Mana Speed");
            return;
        }
        if (currentPlotShown == "Mana Speed")
        {
            ShowLinePlot("Mana");
            return;
        }

        //Math group
        if (currentPlotShown == "Math")
        {
            ShowLinePlot("Math: Add");
            return;
        }
        if (currentPlotShown == "Math: Add")
        {
            ShowLinePlot("Math: Multiply");
            return;
        }
        if (currentPlotShown == "Math: Multiply")
        {
            ShowLinePlot("Math: Coprimes");
            return;
        }
        if (currentPlotShown == "Math: Coprimes")
        {
            ShowLinePlot("Math: Vector");
            return;
        }
        if (currentPlotShown == "Math: Vector")
        {
            ShowLinePlot("Math: Interval");
            return;
        }
        if (currentPlotShown == "Math: Interval")
        {
            ShowLinePlot("Math: Trigonometry");
            return;
        }
        if (currentPlotShown == "Math: Trigonometry")
        {
            ShowLinePlot("Math: Sort");
            return;
        }
        if (currentPlotShown == "Math: Sort")
        {
            ShowLinePlot("Math");
            return;
        }


        //Visual group
        if (currentPlotShown == "Visual")
        {
            ShowLinePlot("Visual: Add");
            return;
        }
        if (currentPlotShown == "Visual: Add")
        {
            ShowLinePlot("Visual: Subtract");
            return;
        }
        if (currentPlotShown == "Visual: Subtract")
        {
            ShowLinePlot("Visual: Gray");
            return;
        }
        if (currentPlotShown == "Visual: Gray")
        {
            ShowLinePlot("Visual: Text");
            return;
        }
        if (currentPlotShown == "Visual: Text")
        {
            ShowLinePlot("Visual");
            return;
        }


        //Spatial group
        if (currentPlotShown == "Spatial")
        {
            ShowLinePlot("Spatial: Triangle");
            return;
        }
        if (currentPlotShown == "Spatial: Triangle")
        {
            ShowLinePlot("Spatial: Rectangle");
            return;
        }
        if (currentPlotShown == "Spatial: Rectangle")
        {
            ShowLinePlot("Spatial: 3 Shapes");
            return;
        }
        if (currentPlotShown == "Spatial: 3 Shapes")
        {
            ShowLinePlot("Spatial: Kanizsa");
            return;
        }
        if (currentPlotShown == "Spatial: Kanizsa")
        {
            ShowLinePlot("Spatial: Angle");
            return;
        }
        if (currentPlotShown == "Spatial: Angle")
        {
            ShowLinePlot("Spatial: Hanoi");
            return;
        }
        if (currentPlotShown == "Spatial: Hanoi")
        {
            ShowLinePlot("Spatial");
            return;
        }

        //Verbal group
        if (currentPlotShown == "Verbal")
        {
            ShowLinePlot("Verbal: Antonym Verbs");
            return;
        }
        if (currentPlotShown == "Verbal: Antonym Verbs")
        {
            ShowLinePlot("Verbal: Antonym Adjectives");
            return;
        }
        if (currentPlotShown == "Verbal: Antonym Adjectives")
        {
            ShowLinePlot("Verbal: Antonym Nouns");
            return;
        }
        if (currentPlotShown == "Verbal: Antonym Nouns")
        {
            ShowLinePlot("Verbal: Synonym Verbs");
            return;
        }
        if (currentPlotShown == "Verbal: Synonym Verbs")
        {
            ShowLinePlot("Verbal: Synonym Adjectives");
            return;
        }
        if (currentPlotShown == "Verbal: Synonym Adjectives")
        {
            ShowLinePlot("Verbal: Grammar");
            return;
        }
        if (currentPlotShown == "Verbal: Grammar")
        {
            ShowLinePlot("Verbal: Question Answer");
            return;
        }
        if (currentPlotShown == "Verbal: Question Answer")
        {
            ShowLinePlot("Verbal: Generate Words");
            return;
        }
        if (currentPlotShown == "Verbal: Generate Words")
        {
            ShowLinePlot("Verbal");
            return;
        }

        //Music group
        if (currentPlotShown == "Music")
        {
            ShowLinePlot("Music: Double Slow");
            return;
        }
        if (currentPlotShown == "Music: Double Slow")
        {
            ShowLinePlot("Music: Single Slow");
            return;
        }
        if (currentPlotShown == "Music: Single Slow")
        {
            ShowLinePlot("Music: Double Fast");
            return;
        }
        if (currentPlotShown == "Music: Double Fast")
        {
            ShowLinePlot("Music: Single Fast");
            return;
        }
        if (currentPlotShown == "Music: Single Fast")
        {
            ShowLinePlot("Music: Tik and Tok");
            return;
        }
        if (currentPlotShown == "Music: Tik and Tok")
        {
            ShowLinePlot("Music: 5 Slots");
            return;
        }
        if (currentPlotShown == "Music: 5 Slots")
        {
            ShowLinePlot("Music");
            return;
        }

        //Memory group
        if (currentPlotShown == "Memory")
        {
            ShowLinePlot("Memory: Easy");
            return;
        }
        if (currentPlotShown == "Memory: Easy")
        {
            ShowLinePlot("Memory: Moderate");
            return;
        }
        if (currentPlotShown == "Memory: Moderate")
        {
            ShowLinePlot("Memory: Hard");
            return;
        }
        if (currentPlotShown == "Memory: Hard")
        {
            ShowLinePlot("Memory");
            return;
        }

        //Physical group
        if (currentPlotShown == "Motor")
        {
            ShowLinePlot("Physical: Fast and Accurate");
            return;
        }
        if (currentPlotShown == "Physical: Fast and Accurate")
        {
            ShowLinePlot("Physical: Visit the Bank");
            return;
        }
        if (currentPlotShown == "Physical: Visit the Bank")
        {
            ShowLinePlot("Physical: Visit All Slots");
            return;
        }
        if (currentPlotShown == "Physical: Visit All Slots")
        {
            ShowLinePlot("Motor");
            return;
        }

    }


    public void ShowPreviousLinePlot()
    {
        //Mana group
        if (currentPlotShown == "Mana Speed")
        {
            ShowLinePlot("Mana");
            return;
        }
        if (currentPlotShown == "Mana")
        {
            ShowLinePlot("Mana Speed");
            return;
        }

        //Math Group
        if (currentPlotShown == "Math: Sort")
        {
            ShowLinePlot("Math: Trigonometry");
            return;
        }
        if (currentPlotShown == "Math: Trigonometry")
        {
            ShowLinePlot("Math: Interval");
            return;
        }
        if (currentPlotShown == "Math: Interval")
        {
            ShowLinePlot("Math: Vector");
            return;
        }
        if (currentPlotShown == "Math: Vector")
        {
            ShowLinePlot("Math: Coprimes");
            return;
        }
        if (currentPlotShown == "Math: Coprimes")
        {
            ShowLinePlot("Math: Multiply");
            return;
        }
        if (currentPlotShown == "Math: Multiply")
        {
            ShowLinePlot("Math: Add");
            return;
        }
        if (currentPlotShown == "Math: Add")
        {
            ShowLinePlot("Math");
            return;
        }
        if (currentPlotShown == "Math")
        {
            ShowLinePlot("Math: Sort");
            return;
        }


        //Visual group
        if (currentPlotShown == "Visual")
        {
            ShowLinePlot("Visual: Text");
            return;
        }
        if (currentPlotShown == "Visual: Add")
        {
            ShowLinePlot("Visual");
            return;
        }
        if (currentPlotShown == "Visual: Subtract")
        {
            ShowLinePlot("Visual: Add");
            return;
        }
        if (currentPlotShown == "Visual: Gray")
        {
            ShowLinePlot("Visual: Subtract");
            return;
        }
        if (currentPlotShown == "Visual: Text")
        {
            ShowLinePlot("Visual: Gray");
            return;
        }

        //Spatial group
        if (currentPlotShown == "Spatial")
        {
            ShowLinePlot("Spatial: Hanoi");
            return;
        }
        if (currentPlotShown == "Spatial: Triangle")
        {
            ShowLinePlot("Spatial");
            return;
        }
        if (currentPlotShown == "Spatial: Rectangle")
        {
            ShowLinePlot("Spatial: Triangle");
            return;
        }
        if (currentPlotShown == "Spatial: 3 Shapes")
        {
            ShowLinePlot("Spatial: Rectangle");
            return;
        }
        if (currentPlotShown == "Spatial: Kanizsa")
        {
            ShowLinePlot("Spatial: 3 Shapes");
            return;
        }
        if (currentPlotShown == "Spatial: Angle")
        {
            ShowLinePlot("Spatial: Kanizsa");
            return;
        }
        if (currentPlotShown == "Spatial: Hanoi")
        {
            ShowLinePlot("Spatial: Angle");
            return;
        }

        //Verbal group
        if (currentPlotShown == "Verbal")
        {
            ShowLinePlot("Verbal: Generate Words");
            return;
        }
        if (currentPlotShown == "Verbal: Antonym Verbs")
        {
            ShowLinePlot("Verbal");
            return;
        }
        if (currentPlotShown == "Verbal: Antonym Adjectives")
        {
            ShowLinePlot("Verbal: Antonym Verbs");
            return;
        }
        if (currentPlotShown == "Verbal: Antonym Nouns")
        {
            ShowLinePlot("Verbal: Antonym Adjectives");
            return;
        }
        if (currentPlotShown == "Verbal: Synonym Verbs")
        {
            ShowLinePlot("Verbal: Antonym Nouns");
            return;
        }
        if (currentPlotShown == "Verbal: Synonym Adjectives")
        {
            ShowLinePlot("Verbal: Synonym Verbs");
            return;
        }
        if (currentPlotShown == "Verbal: Grammar")
        {
            ShowLinePlot("Verbal: Synonym Adjectives");
            return;
        }
        if (currentPlotShown == "Verbal: Question Answer")
        {
            ShowLinePlot("Verbal: Grammar");
            return;
        }
        if (currentPlotShown == "Verbal: Generate Words")
        {
            ShowLinePlot("Verbal: Question Answer");
            return;
        }

        //Music group
        if (currentPlotShown == "Music")
        {
            ShowLinePlot("Music: 5 Slots");
            return;
        }
        if (currentPlotShown == "Music: Double Slow")
        {
            ShowLinePlot("Music");
            return;
        }
        if (currentPlotShown == "Music: Single Slow")
        {
            ShowLinePlot("Music: Double Slow");
            return;
        }
        if (currentPlotShown == "Music: Double Fast")
        {
            ShowLinePlot("Music: Single Slow");
            return;
        }
        if (currentPlotShown == "Music: Single Fast")
        {
            ShowLinePlot("Music: Double Fast");
            return;
        }
        if (currentPlotShown == "Music: Tik and Tok")
        {
            ShowLinePlot("Music: Single Fast");
            return;
        }
        if (currentPlotShown == "Music: 5 Slots")
        {
            ShowLinePlot("Music: Tik and Tok");
            return;
        }

        //Memory group
        if (currentPlotShown == "Memory")
        {
            ShowLinePlot("Memory: Hard");
            return;
        }
        if (currentPlotShown == "Memory: Easy")
        {
            ShowLinePlot("Memory");
            return;
        }
        if (currentPlotShown == "Memory: Moderate")
        {
            ShowLinePlot("Memory: Easy");
            return;
        }
        if (currentPlotShown == "Memory: Hard")
        {
            ShowLinePlot("Memory: Moderate");
            return;
        }

        //Physical group
        if (currentPlotShown == "Motor")
        {
            ShowLinePlot("Physical: Visit All Slots");
            return;
        }
        if (currentPlotShown == "Physical: Fast and Accurate")
        {
            ShowLinePlot("Motor");
            return;
        }
        if (currentPlotShown == "Physical: Visit the Bank")
        {
            ShowLinePlot("Physical: Fast and Accurate");
            return;
        }
        if (currentPlotShown == "Physical: Visit All Slots")
        {
            ShowLinePlot("Physical: Visit the Bank");
            return;
        }


    }



}
