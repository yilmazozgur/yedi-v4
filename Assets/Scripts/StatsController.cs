//using System.Collections;
//using System.Collections.Generic;
//using UnityEngine;
//using BayatGames.SaveGameFree;
//using ChartUtil.Demo;

//public class StatsController : MonoBehaviour
//{
//    public float avgPersonTotal = 8f;
//    public float avgPersonNumber = 2.5f;
//    public float avgPersonColor = 2f;
//    public float avgPersonShape = 2f;
//    public float avgPersonWord = 1.5f;
//    public float avgPersonBeat = 2f;
//    public float avgPersonMemory = 2f;
//    public float avgPersonMotor = 2f;

//    public float stdPersonTotal = 1f;
//    public float stdPersonNumber = 1f;
//    public float stdPersonColor = 1f;
//    public float stdPersonShape = 1f;
//    public float stdPersonWord = 1f;
//    public float stdPersonBeat = 1f;
//    public float stdPersonMemory = 1f;
//    public float stdPersonMotor = 1f;

//    // For keeping track during game play
//    public float manaValueMax = 0f;
//    public float manaPerTimeMax = 0f;
//    public float numberOfMerges = 0;
//    public float numberGain = 0f;
//    public float colorGain = 0f;
//    public float shapeGain = 0f;
//    public float wordGain = 0f;
//    public float beatGain = 0f;
//    public float memoryGain = 0f;
//    public float motorGain = 0f;
//    public float numberGainNorm = 0f;
//    public float colorGainNorm = 0f;
//    public float shapeGainNorm = 0f;
//    public float wordGainNorm = 0f;
//    public float beatGainNorm = 0f;
//    public float memoryGainNorm = 0f;
//    public float motorGainNorm = 0f;


//    public int numberOfGamesPlayed = 0;
//    float manaCollectedTotal = 0f;
//    List<float> manaValueMaxList = new List<float>();
//    List<float> manaPerTimeMaxList = new List<float>();
//    List<float> numberGainList = new List<float>();
//    List<float> colorGainList = new List<float>();
//    List<float> shapeGainList = new List<float>();
//    List<float> wordGainList = new List<float>();
//    List<float> beatGainList = new List<float>();
//    List<float> memoryGainList = new List<float>();
//    List<float> motorGainList = new List<float>();
//    float numberGainAvg = 0;
//    float colorGainAvg = 0;
//    float shapeGainAvg = 0;
//    float wordGainAvg = 0;
//    float beatGainAvg = 0;
//    float memoryGainAvg = 0;
//    float motorGainAvg = 0;

//    public static ChartUtil.Chart chartStats;
//    public static ChartUtil.Chart chartDistribution;
//    public static ChartUtil.Chart chartRanking;
//    public static ChartUtil.ChartData chartData;
//    public static ChartUtil.ChartData chartDistributionData;
//    public static ChartUtil.ChartData chartRankingData;

//    ChartUtil.Series manaValueSeries = new ChartUtil.Series();
//    ChartUtil.Series manaPerTimeSeries = new ChartUtil.Series();
//    ChartUtil.Series numberGainSeries = new ChartUtil.Series();
//    ChartUtil.Series colorGainSeries = new ChartUtil.Series();
//    ChartUtil.Series shapeGainSeries = new ChartUtil.Series();
//    ChartUtil.Series wordGainSeries = new ChartUtil.Series();
//    ChartUtil.Series beatGainSeries = new ChartUtil.Series();
//    ChartUtil.Series memoryGainSeries = new ChartUtil.Series();
//    ChartUtil.Series motorGainSeries = new ChartUtil.Series();
//    ChartUtil.Series distributionNumberSeries = new ChartUtil.Series();
//    ChartUtil.Series distributionColorSeries = new ChartUtil.Series();
//    ChartUtil.Series distributionShapeSeries = new ChartUtil.Series();
//    ChartUtil.Series distributionWordSeries = new ChartUtil.Series();
//    ChartUtil.Series distributionBeatSeries = new ChartUtil.Series();
//    ChartUtil.Series distributionMemorySeries = new ChartUtil.Series();
//    ChartUtil.Series distributionMotorSeries = new ChartUtil.Series();
//    ChartUtil.Series rankingSeries = new ChartUtil.Series();

//    static List<string> chartDistributionCategories = new List<string> { "Math", "Visual", "Spatial", "Verbal" , "Music", "Memory", "Motor"};
//    static List<string> chartRankingCategories = new List<string> { "Overall", "Math", "Visual", "Spatial", "Verbal", "Music", "Memory", "Motor" };
//    static List<string> chartValuesCategories = new List<string>();

//    ResetDialogCanvas resetDialogCanvas;

//    void Start()
//    {
//        resetDialogCanvas = FindObjectOfType<ResetDialogCanvas>();
//        if(resetDialogCanvas)
//        {
//            resetDialogCanvas.gameObject.SetActive(false);
//        }

//        if (SaveGame.Exists("manaCollectedTotal"))
//        {
//            manaCollectedTotal = SaveGame.Load<float>("manaCollectedTotal");
//        }

//        if (SaveGame.Exists("manaValueMaxList"))
//        {
//            manaValueMaxList = SaveGame.Load<List<float>>("manaValueMaxList");
//            numberOfGamesPlayed = manaValueMaxList.Count;
//            //Debug.Log(numberOfGamesPlayed);
//            SaveGame.Save<int>("numberOfGamesPlayed", numberOfGamesPlayed);
//        }

//        if (SaveGame.Exists("manaPerTimeMaxList"))
//        {
//            manaPerTimeMaxList = SaveGame.Load<List<float>>("manaPerTimeMaxList");
//        }

//        if (SaveGame.Exists("numberGainList"))
//        {
//            numberGainList = SaveGame.Load<List<float>>("numberGainList");
//        }

//        if (SaveGame.Exists("colorGainList"))
//        {
//            colorGainList = SaveGame.Load<List<float>>("colorGainList");
//        }

//        if (SaveGame.Exists("shapeGainList"))
//        {
//            shapeGainList = SaveGame.Load<List<float>>("shapeGainList");
//        }

//        if (SaveGame.Exists("wordGainList"))
//        {
//            wordGainList = SaveGame.Load<List<float>>("wordGainList");
//        }

//        if (SaveGame.Exists("beatGainList"))
//        {
//            beatGainList = SaveGame.Load<List<float>>("beatGainList");
//        }

//        if (SaveGame.Exists("memoryGainList"))
//        {
//            memoryGainList = SaveGame.Load<List<float>>("memoryGainList");
//        }

//        if (SaveGame.Exists("motorGainList"))
//        {
//            motorGainList = SaveGame.Load<List<float>>("motorGainList");
//        }

//        // Graph/Chart Init
//        ChartUtil.Chart[] chartsAll = FindObjectsOfType<ChartUtil.Chart>();
//        foreach(ChartUtil.Chart chartIter in chartsAll)
//        {
//            if (chartIter.gameObject.name == "Chart Line")
//            {
//                chartStats = chartIter;
//                chartData = chartStats.GetComponentInParent<ChartUtil.ChartData>();
//                if(chartValuesCategories.Count != manaValueMaxList.Count)
//                {
//                    int time_pt = 0;
//                    for (int i = 0; i <= manaValueMaxList.Count - 1; i++)
//                    {
//                        time_pt = i + 1;
//                        chartValuesCategories.Add(time_pt.ToString());
//                    }
//                }
                
//                chartData.series = new List<ChartUtil.Series>();
//                PrepareManaValueData();
//                PrepareManaPerTimeData();
//                PrepareNumberGainData();
//                PrepareColorGainData();
//                PrepareShapeGainData();
//                PrepareWordGainData();
//                PrepareBeatGainData();
//                PrepareMemoryGainData();
//                PrepareMotorGainData();
//            }
//            else if (chartIter.gameObject.name == "Chart Distribution")
//            {
//                chartDistribution = chartIter;
//                chartDistributionData = chartDistribution.GetComponentInParent<ChartUtil.ChartData>();
//                chartDistributionData.series = new List<ChartUtil.Series>();
//                PrepareDistributionData();
//            }
//            else if (chartIter.gameObject.name == "Chart Ranking")
//            {
//                chartRanking = chartIter;
//                chartRankingData = chartRanking.GetComponentInParent<ChartUtil.ChartData>();
//                chartRankingData.series = new List<ChartUtil.Series>();
//                PrepareRankingData();
//            }
//        }

//        if (chartsAll.Length > 0)
//        {
//            ShowManaPlot();
//        }

//        //Debug.Log("End of Stats Start method");
//        //Debug.Log(numberOfGamesPlayed);

//    }

//    public void ShowResetDialog()
//    {
//        resetDialogCanvas.gameObject.SetActive(true);
//        resetDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(true);
//    }

//    public void HideResetDialog()
//    {
//        resetDialogCanvas.gameObject.SetActive(false);
//        resetDialogCanvas.GetComponentInChildren<Canvas>().gameObject.SetActive(false);
//    }

//    public void UpdateMaxManaValue(float maxManaValueUpdate)
//    {
//        manaValueMax = maxManaValueUpdate;
//    }

//    public void UpdateMaxManaPerTime(float maxmanaPerTimeUpdate)
//    {
//        manaPerTimeMax = maxmanaPerTimeUpdate;
//    }

//    public void UpdateNumberofMerges(float numberOfMergesUpdate)
//    {
//        numberOfMerges = numberOfMergesUpdate;
//    }

//    public void UpdateGains(float numberGainUpdate, float colorGainUpdate,
//        float shapeGainUpdate, float wordGainUpdate, float beatGainUpdate,
//        float memoryGainUpdate, float motorGainUpdate)
//    {
//        numberGain = numberGainUpdate;
//        colorGain = colorGainUpdate;
//        shapeGain = shapeGainUpdate;
//        wordGain = wordGainUpdate;
//        beatGain = beatGainUpdate;
//        memoryGain = memoryGainUpdate;
//        motorGain = motorGainUpdate;
//    }
     
//    public (float numberGain, float colorGain, float shapeGain, float wordGain,
//        float beatGain, float memoryGain, float motorGain) NormalizeGains()
//    {
//        numberGainNorm = (numberGain) / (numberOfMerges + 1f);
//        numberGainNorm = (numberGainNorm + 1f) / 4f;
//        colorGainNorm = (colorGain) / (numberOfMerges + 1f);
//        colorGainNorm = (colorGainNorm + 1f) / 4f;
//        shapeGainNorm = (shapeGain) / (numberOfMerges + 1);
//        shapeGainNorm = (shapeGainNorm + 1f) / 4f;
//        wordGainNorm = (wordGain) / (numberOfMerges + 1f);
//        wordGainNorm = (wordGainNorm + 1f) / 4f;
//        beatGainNorm = (beatGain) / (numberOfMerges + 1f);
//        beatGainNorm = (beatGainNorm + 1f) / 4f;
//        memoryGainNorm = (memoryGain) / (numberOfMerges + 1f);
//        memoryGainNorm = (memoryGainNorm + 1f) / 4f;
//        motorGainNorm = (motorGain) / (numberOfMerges + 1f);
//        motorGainNorm = (motorGainNorm + 1f) / 4f;
//        return (numberGainNorm, colorGainNorm, shapeGainNorm, wordGainNorm, beatGainNorm, memoryGainNorm, motorGainNorm);
//    }

//    public void SaveGameStats(bool numberActive, bool colorActive,
//        bool shapeActive, bool wordActive, bool beatActive, bool memoryActive, bool motorActive,
//        string modeNumber, string modeColor, string modeShape, string modeWord,
//        string modeBeat, string modeMemory, string modeMotor)
//    {
//        manaValueMaxList.Add(manaValueMax);
//        SaveGame.Save<List<float>>("manaValueMaxList", manaValueMaxList);

//        manaPerTimeMaxList.Add(manaPerTimeMax);
//        SaveGame.Save<List<float>>("manaPerTimeMaxList", manaPerTimeMaxList);

//        (numberGainNorm, colorGainNorm, shapeGainNorm, wordGainNorm, beatGainNorm, memoryGainNorm, motorGainNorm) = NormalizeGains();

//        if(numberActive)
//        {
//            numberGainList.Add(numberGainNorm);
//            SaveGame.Save<List<float>>("numberGainList", numberGainList);
//        }
        
//        if(colorActive)
//        {
//            colorGainList.Add(colorGainNorm);
//            SaveGame.Save<List<float>>("colorGainList", colorGainList);
//        }
        
//        if(shapeActive)
//        {
//            shapeGainList.Add(shapeGainNorm);
//            SaveGame.Save<List<float>>("shapeGainList", shapeGainList);
//        }
        
//        if(wordActive)
//        {
//            wordGainList.Add(wordGainNorm);
//            SaveGame.Save<List<float>>("wordGainList", wordGainList);
//        }
        
//        if(beatActive)
//        {
//            beatGainList.Add(beatGainNorm);
//            SaveGame.Save<List<float>>("beatGainList", beatGainList);
//        }

//        if (memoryActive)
//        {
//            memoryGainList.Add(memoryGainNorm);
//            SaveGame.Save<List<float>>("memoryGainList", memoryGainList);
//        }

//        if (motorActive)
//        {
//            motorGainList.Add(motorGainNorm);
//            SaveGame.Save<List<float>>("motorGainList", motorGainList);
//        }
//    }

//    public void PrepareManaValueData()
//    {
//        manaValueSeries.name = "Max Mana";
       
//        foreach (float dataPoint in manaValueMaxList)
//        {
//            manaValueSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            manaCollectedTotal = manaCollectedTotal + Mathf.Round(dataPoint);
//        }
//        Debug.Log(manaCollectedTotal);
//        chartData.series.Add(manaValueSeries);
//        chartData.categories = chartValuesCategories;

//    }

//    public void PrepareManaPerTimeData()
//    {
//        manaPerTimeSeries.name = "Mana Per Sec";
        
//        foreach (float dataPoint in manaPerTimeMaxList)
//        {
//            manaPerTimeSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//        }
//        chartData.series.Add(manaPerTimeSeries);

//    }

//    public void PrepareNumberGainData()
//    {
//        numberGainSeries.name = "Math";

//        foreach (float dataPoint in numberGainList)
//        {
//            numberGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            numberGainAvg += dataPoint;
//        }
//        chartData.series.Add(numberGainSeries);
//        numberGainAvg = numberGainAvg / (numberGainList.Count + 1f);

//    }

//    public void PrepareColorGainData()
//    {
//        colorGainSeries.name = "Visual";

//        foreach (float dataPoint in colorGainList)
//        {
//            colorGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            colorGainAvg += dataPoint;
//        }
//        chartData.series.Add(colorGainSeries);
//        colorGainAvg = colorGainAvg / (colorGainList.Count + 1f);

//    }

//    public void PrepareShapeGainData()
//    {
//        shapeGainSeries.name = "Spatial";

//        foreach (float dataPoint in shapeGainList)
//        {
//            shapeGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            shapeGainAvg += dataPoint;
//        }
//        chartData.series.Add(shapeGainSeries);
//        shapeGainAvg = shapeGainAvg / (shapeGainList.Count + 1);

//    }

//    public void PrepareWordGainData()
//    {
//        wordGainSeries.name = "Verbal";

//        foreach (float dataPoint in wordGainList)
//        {
//            wordGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            wordGainAvg += dataPoint;
//        }
//        chartData.series.Add(wordGainSeries);
//        wordGainAvg = wordGainAvg / (wordGainList.Count + 1);

//    }

//    public void PrepareBeatGainData()
//    {
//        beatGainSeries.name = "Music";

//        foreach (float dataPoint in beatGainList)
//        {
//            beatGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            beatGainAvg += dataPoint;
//        }
//        chartData.series.Add(beatGainSeries);
//        beatGainAvg = beatGainAvg / (beatGainList.Count + 1);

//    }

//    public void PrepareMemoryGainData()
//    {
//        memoryGainSeries.name = "Memory";

//        foreach (float dataPoint in memoryGainList)
//        {
//            memoryGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            memoryGainAvg += dataPoint;
//        }
//        chartData.series.Add(memoryGainSeries);
//        memoryGainAvg = memoryGainAvg / (memoryGainList.Count + 1);

//    }

//    public void PrepareMotorGainData()
//    {
//        motorGainSeries.name = "Motor";

//        foreach (float dataPoint in motorGainList)
//        {
//            motorGainSeries.data.Add(new ChartUtil.Data(Mathf.Round(dataPoint)));
//            motorGainAvg += dataPoint;
//        }
//        chartData.series.Add(motorGainSeries);
//        motorGainAvg = motorGainAvg / (motorGainList.Count + 1);

//    }

//    public float ApplyLogistic(float GainPerson, float GainMean, float GainStd)
//    {
//        return Mathf.Round(100f / (1f + Mathf.Exp(-GainStd * (GainPerson - GainMean))));
//    }

//    public void PrepareDistributionData()
//    {
//        float totalValue = (ApplyLogistic(numberGainAvg, avgPersonNumber, stdPersonNumber) +
//            ApplyLogistic(colorGainAvg, avgPersonColor, stdPersonColor) +
//            ApplyLogistic(shapeGainAvg, avgPersonShape, stdPersonShape) +
//            ApplyLogistic(wordGainAvg, avgPersonWord, stdPersonWord) +
//            ApplyLogistic(beatGainAvg, avgPersonBeat, stdPersonBeat) +
//            ApplyLogistic(memoryGainAvg, avgPersonMemory, stdPersonMemory) +
//            ApplyLogistic(motorGainAvg, avgPersonMotor, stdPersonMotor)) + 0.0001f;
//        distributionNumberSeries.name = "Math";
//        distributionNumberSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(numberGainAvg, avgPersonNumber, stdPersonNumber) / totalValue)));
//        distributionColorSeries.name = "Visual";
//        distributionColorSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(colorGainAvg, avgPersonColor, stdPersonColor) / totalValue)));
//        distributionShapeSeries.name = "Spatial";
//        distributionShapeSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(shapeGainAvg, avgPersonShape, stdPersonShape) / totalValue)));
//        distributionWordSeries.name = "Verbal";
//        distributionWordSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(wordGainAvg, avgPersonWord, stdPersonWord) / totalValue)));
//        distributionBeatSeries.name = "Music";
//        distributionBeatSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(beatGainAvg, avgPersonBeat, stdPersonBeat) / totalValue)));
//        distributionMemorySeries.name = "Memory";
//        distributionMemorySeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(memoryGainAvg, avgPersonMemory, stdPersonMemory) / totalValue)));
//        distributionMotorSeries.name = "Motor";
//        distributionMotorSeries.data.Add(new ChartUtil.Data(Mathf.Round(100f * ApplyLogistic(motorGainAvg, avgPersonMotor, stdPersonMotor) / totalValue)));

//        chartDistributionData.categories = chartDistributionCategories;

//        chartDistributionData.series.Add(distributionNumberSeries);
//        chartDistributionData.series.Add(distributionColorSeries);
//        chartDistributionData.series.Add(distributionShapeSeries);
//        chartDistributionData.series.Add(distributionWordSeries);
//        chartDistributionData.series.Add(distributionBeatSeries);
//        chartDistributionData.series.Add(distributionMemorySeries);
//        chartDistributionData.series.Add(distributionMotorSeries);

//    }

//    public void PrepareRankingData()
//    {
//        float totalValue = numberGainAvg + colorGainAvg + shapeGainAvg + wordGainAvg + beatGainAvg + memoryGainAvg + motorGainAvg;
        
//        rankingSeries.name = "Ranking";
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(totalValue, avgPersonTotal, stdPersonTotal) -1f )); 
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(numberGainAvg, avgPersonNumber, stdPersonNumber) -1f ));
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(colorGainAvg, avgPersonColor, stdPersonColor) -1f ));
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(shapeGainAvg, avgPersonShape, stdPersonShape) -1f));
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(wordGainAvg, avgPersonWord, stdPersonWord) -1f));
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(beatGainAvg, avgPersonBeat, stdPersonBeat) -1f));
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(memoryGainAvg, avgPersonMemory, stdPersonMemory) -1f));
//        rankingSeries.data.Add(new ChartUtil.Data(ApplyLogistic(motorGainAvg, avgPersonMotor, stdPersonMotor) -1f));

//        chartRankingData.categories = chartRankingCategories;
//        chartRankingData.series.Add(rankingSeries);
//    }

//    public void ShowManaPlot()
//    {
//        if(numberOfGamesPlayed>0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            //chartDistribution.enabled = false;
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Max Mana")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }


//    }

//    public void ShowManaPerTimePlot()
//    {
//        //Debug.Log(numberOfGamesPlayed);
//        if (numberOfGamesPlayed > 0)
//        {
//            //Debug.Log("Speed Plot");
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Mana Per Sec")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowNumberPlot()
//    {
//        //Debug.Log(numberOfGamesPlayed);
//        if (numberOfGamesPlayed > 0)
//        {
//            //Debug.Log("Math Plot");
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Math")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowColorPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Visual")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowShapePlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Spatial")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowWordPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Verbal")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowBeatPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Music")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowMemoryPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Memory")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowMotorPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(true);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartData.series)
//            {
//                if (seriesChart.name == "Motor")
//                {
//                    seriesChart.show = true;
//                }
//                else
//                {
//                    seriesChart.show = false;
//                }

//            }

//            //update chart
//            chartStats.UpdateChart();
//        }
        
//    }

//    public void ShowDistributionPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(false);
//            chartDistribution.gameObject.SetActive(true);
//            chartRanking.gameObject.SetActive(false);
//            foreach (var seriesChart in chartDistributionData.series)
//            {
//                seriesChart.show = true;
//            }

//            //update chart
//            chartDistribution.UpdateChart();
//        }
        
//    }

//    public void ShowRankingPlot()
//    {
//        if (numberOfGamesPlayed > 0)
//        {
//            chartStats.gameObject.SetActive(false);
//            chartDistribution.gameObject.SetActive(false);
//            chartRanking.gameObject.SetActive(true);
//            foreach (var seriesChart in chartRankingData.series)
//            {
//                seriesChart.show = true;
//            }

//            //update chart
//            chartRanking.UpdateChart();
//        }
        
//    }

//    public void ResetAllStats()
//    {
//        SaveGame.Delete("manaValueMaxList");
//        SaveGame.Delete("manaPerTimeMaxList");
//        SaveGame.Delete("numberGainList");
//        SaveGame.Delete("colorGainList");
//        SaveGame.Delete("shapeGainList");
//        SaveGame.Delete("wordGainList");
//        SaveGame.Delete("beatGainList");
//        SaveGame.Delete("memoryGainList");
//        SaveGame.Delete("motorGainList");
//        numberOfGamesPlayed = 0;
//        HideResetDialog();

//    }

//}
