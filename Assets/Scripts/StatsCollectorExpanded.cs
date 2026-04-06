using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class StatsCollectorExpanded : MonoBehaviour
{
    public static StatsCollectorExpanded Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    StatsControllerExpanded statsControllerExpanded;
    LevelController levelController;
    Text gameResultManaText;
    Text gameResultManaSpeedText;
    Text gameResultMathText;
    Text gameResultColorText;
    Text gameResultSpatialText;
    Text gameResultVerbalText;
    Text gameResultMusicText;
    Text gameResultMemoryText;
    Text gameResultMotorText;
    Text gameResultTitleTextMath;
    Text gameResultTitleTextColor;
    Text gameResultTitleTextSpatial;
    Text gameResultTitleTextVerbal;
    Text gameResultTitleTextMusic;
    Text gameResultTitleTextMemory;
    Text gameResultTitleTextMotor;

    Color colorMathValueText;
    Color colorMathTitleText;
    Color colorColorValueText;
    Color colorColorTitleText;
    Color colorSpatialValueText;
    Color colorSpatialTitleText;
    Color colorVerbalValueText;
    Color colorVerbalTitleText;
    Color colorMusicValueText;
    Color colorMusicTitleText;
    Color colorMemoryValueText;
    Color colorMemoryTitleText;
    Color colorMotorValueText;
    Color colorMotorTitleText;

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

    static List<string> chartLineTypesCode = new List<string> { "Mana", "Mana Speed",
        "Math", "Visual", "Spatial", "Verbal", "Music", "Memory", "Motor",
        "addM", "multiply", "gcd", "vector", "interval", "trigon", "sort" ,
        "addV", "subtract", "gray", "text",
        "triangle", "rectangle", "triple", "kanizsa", "sphere", "hanoi",
        "verbs", "adjectives", "nouns", "synVerbs", "synAdjectives", "grammar", "questions", "scrabble",
        "double", "single", "double fast", "single fast", "tiktok", "five",
        "every action", "show all", "show one",
        "speed accuracy", "speed accuracy halfway", "visit all slots"};

    List<float> listMean = new List<float>();
    List<float> listStd = new List<float>();
    float avgGeneric;
    float stdGeneric;
    float avgPersonTotal = 8f;
    float avgPersonNumber;
    float avgPersonColor;
    float avgPersonShape;
    float avgPersonWord;
    float avgPersonBeat;
    float avgPersonMemory;
    float avgPersonMotor;

    float stdPersonTotal = 0.025f;
    float stdPersonNumber;
    float stdPersonColor;
    float stdPersonShape;
    float stdPersonWord;
    float stdPersonBeat;
    float stdPersonMemory;
    float stdPersonMotor;

    Dictionary<string, float> dataCurrentGame = new Dictionary<string, float>();

    public float numberOfMerges = 0f;

    void Start()
    {
        
        if (dataCurrentGame.ContainsKey("Physical: Visit All Slots") == false)
        {
            foreach (string lineChartName in chartLineTypes)
            {
                dataCurrentGame.Add(lineChartName, 0f);
            }
        }

        statsControllerExpanded = StatsControllerExpanded.Instance;
        avgGeneric = statsControllerExpanded.GetAvgGeneric();
        stdGeneric = statsControllerExpanded.GetStdGeneric();
        PrepareMeanAndStd();
        levelController = LevelController.Instance;
        // Mana display owned by ScoreManager for "Best" score; hide Mana Speed
        gameResultManaText = null;
        gameResultManaSpeedText = null;
        GameResultManaSpeed gameResultManaSpeed = FindAnyObjectByType<GameResultManaSpeed>();
        if (gameResultManaSpeed != null) gameResultManaSpeed.gameObject.SetActive(false);
        gameResultMathText = FindAnyObjectByType<GameResultMath>().GetComponent<Text>();
        gameResultColorText = FindAnyObjectByType<GameResultColor>().GetComponent<Text>();
        gameResultSpatialText = FindAnyObjectByType<GameResultSpatial>().GetComponent<Text>();
        gameResultVerbalText = FindAnyObjectByType<GameResultVerbal>().GetComponent<Text>();
        gameResultMusicText = FindAnyObjectByType<GameResultMusic>().GetComponent<Text>();
        gameResultMemoryText = FindAnyObjectByType<GameResultMemory>().GetComponent<Text>();
        gameResultMotorText = FindAnyObjectByType<GameResultMotor>().GetComponent<Text>();

        gameResultTitleTextMath = FindAnyObjectByType<GameResultMath>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
        gameResultTitleTextColor = FindAnyObjectByType<GameResultColor>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
        gameResultTitleTextSpatial = FindAnyObjectByType<GameResultSpatial>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
        gameResultTitleTextVerbal = FindAnyObjectByType<GameResultVerbal>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
        gameResultTitleTextMusic = FindAnyObjectByType<GameResultMusic>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
        gameResultTitleTextMemory = FindAnyObjectByType<GameResultMemory>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
        gameResultTitleTextMotor = FindAnyObjectByType<GameResultMotor>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();

        colorMathValueText = gameResultMathText.color;
        gameResultMathText.text = "---";
        colorMathValueText.a = 0.1f;
        gameResultMathText.color = colorMathValueText;
        gameResultTitleTextMath.color = colorMathValueText;

        colorColorValueText = gameResultColorText.color;
        gameResultColorText.text = "---";
        colorColorValueText.a = 0.1f;
        gameResultColorText.color = colorColorValueText;
        gameResultTitleTextColor.color = colorColorValueText;

        colorSpatialValueText = gameResultSpatialText.color;
        gameResultSpatialText.text = "---";
        colorSpatialValueText.a = 0.1f;
        gameResultSpatialText.color = colorSpatialValueText;
        gameResultTitleTextSpatial.color = colorSpatialValueText;

        colorVerbalValueText = gameResultVerbalText.color;
        gameResultVerbalText.text = "---";
        colorVerbalValueText.a = 0.1f;
        gameResultVerbalText.color = colorVerbalValueText;
        gameResultTitleTextVerbal.color = colorVerbalValueText;

        colorMusicValueText = gameResultMusicText.color;
        gameResultMusicText.text = "---";
        colorMusicValueText.a = 0.1f;
        gameResultMusicText.color = colorMusicValueText;
        gameResultTitleTextMusic.color = colorMusicValueText;

        colorMemoryValueText = gameResultMemoryText.color;
        gameResultMemoryText.text = "---";
        colorMemoryValueText.a = 0.1f;
        gameResultMemoryText.color = colorMemoryValueText;
        gameResultTitleTextMemory.color = colorMemoryValueText;

        colorMotorValueText = gameResultMotorText.color;
        gameResultMotorText.text = "---";
        colorMotorValueText.a = 0.1f;
        gameResultMotorText.color = colorMotorValueText;
        gameResultTitleTextMotor.color = colorMotorValueText;

        UpdateMaxManaValue(200f);
        UpdateMaxManaPerTime(0f);
        UpdateStatsScreen();
    }

    public void UpdateMaxManaValue(float maxManaValueUpdate)
    {
        dataCurrentGame["Mana"] = maxManaValueUpdate;
        statsControllerExpanded.UpdateDataGeneric("Mana", maxManaValueUpdate);
        if(gameResultManaText)
        {
            gameResultManaText.text = ((int)maxManaValueUpdate).ToString();
        }
    }

    public void UpdateMaxManaPerTime(float maxmanaPerTimeUpdate)
    {
        dataCurrentGame["Mana Speed"] = maxmanaPerTimeUpdate;
        statsControllerExpanded.UpdateDataGeneric("Mana Speed", maxmanaPerTimeUpdate);
        if(gameResultManaSpeedText)
        {
            gameResultManaSpeedText.text = ((int)maxmanaPerTimeUpdate).ToString();
        }
    }



    private void PrepareMeanAndStd()
    {
        avgGeneric = statsControllerExpanded.GetAvgGeneric();
        stdGeneric = statsControllerExpanded.GetStdGeneric();
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
            else if (i == 20 || i == 21 || i == 22 || i == 23 || i == 38)
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


    public void UpdateStatsScreen()
    {
        float numberGain = dataCurrentGame["Math"] / (numberOfMerges + 1f);
        float colorGain = dataCurrentGame["Visual"] / (numberOfMerges + 1f);
        float shapeGain = dataCurrentGame["Spatial"] / (numberOfMerges + 1f);
        float wordGain = dataCurrentGame["Verbal"] / (numberOfMerges + 1f);
        float beatGain = dataCurrentGame["Music"] / (numberOfMerges + 1f);
        float memoryGain = dataCurrentGame["Memory"] / (numberOfMerges + 1f);
        float motorGain = dataCurrentGame["Motor"] / (numberOfMerges + 1f);

        float numberGainRanking = statsControllerExpanded.ApplyLogistic((numberGain), listMean[2], listStd[2]) - 1f;
        float colorGainRanking = statsControllerExpanded.ApplyLogistic((colorGain), listMean[3], listStd[3]) - 1f;
        float shapeGainRanking = statsControllerExpanded.ApplyLogistic((shapeGain), listMean[4], listStd[4]) - 1f;
        float wordGainRanking = statsControllerExpanded.ApplyLogistic((wordGain), listMean[5], listStd[5]) - 1f;
        float beatGainRanking = statsControllerExpanded.ApplyLogistic((beatGain), listMean[6], listStd[6]) - 1f;
        float memoryGainRanking = statsControllerExpanded.ApplyLogistic((memoryGain), listMean[7], listStd[7]) - 1f;
        float motorGainRanking = statsControllerExpanded.ApplyLogistic((motorGain), listMean[8], listStd[8]) - 1f;

        if (levelController.numberActive)
        {
            colorMathValueText.a = 1f;
            gameResultMathText.color = colorMathValueText;
            gameResultTitleTextMath.color = colorMathValueText;
            gameResultMathText.text = "%" + numberGainRanking.ToString() + " / ( " + Mathf.Round(numberGain * 100f).ToString() + " )";
        }


        if (levelController.colorActive)
        {
            colorColorValueText.a = 1f;
            gameResultColorText.color = colorColorValueText;
            gameResultTitleTextColor.color = colorColorValueText;
            gameResultColorText.text = "%" + colorGainRanking.ToString() + " / ( " + Mathf.Round(colorGain * 100f).ToString() + " )";
        }

        if (levelController.shapeActive)
        {
            colorSpatialValueText.a = 1f;
            gameResultSpatialText.color = colorSpatialValueText;
            gameResultTitleTextSpatial.color = colorSpatialValueText;
            gameResultSpatialText.text = "%" + shapeGainRanking.ToString() + " / ( " + Mathf.Round(shapeGain * 100f).ToString() + " )";
        }

        if (levelController.wordActive)
        {
            colorVerbalValueText.a = 1f;
            gameResultVerbalText.color = colorVerbalValueText;
            gameResultTitleTextVerbal.color = colorVerbalValueText;
            gameResultVerbalText.text = "%" + wordGainRanking.ToString() + " / ( " + Mathf.Round(wordGain * 100f).ToString() + " )";
        }

        if (levelController.beatActive)
        {
            colorMusicValueText.a = 1f;
            gameResultMusicText.color = colorMusicValueText;
            gameResultTitleTextMusic.color = colorMusicValueText;
            gameResultMusicText.text = "%" + beatGainRanking.ToString() + " / ( " + Mathf.Round(beatGain * 100f).ToString() + " )";
        }

        if (levelController.memoryActive)
        {
            colorMemoryValueText.a = 1f;
            gameResultMemoryText.color = colorMemoryValueText;
            gameResultTitleTextMemory.color = colorMemoryValueText;
            gameResultMemoryText.text = "%" + memoryGainRanking.ToString() + " / ( " + Mathf.Round(memoryGain * 100f).ToString() + " )";
        }

        if (levelController.motorActive)
        {
            colorMotorValueText.a = 1f;
            gameResultMotorText.color = colorMotorValueText;
            gameResultTitleTextMotor.color = colorMotorValueText;
            gameResultMotorText.text = "%" + motorGainRanking.ToString() + " / ( " + Mathf.Round(motorGain * 100f).ToString() + " )";
        }
    }

    public void UpdateGameStats(Dictionary<string, float> dataFromMerge, bool mergeOperation)
    {
        //if(mergeOperation == true)
        //{
        //    numberOfMerges += 1;
        //    statsControllerExpanded.UpdateNumberOfMerges(numberOfMerges);
        //}
        numberOfMerges += 1;
        statsControllerExpanded.UpdateNumberOfMerges(numberOfMerges);

        int iter_index = 0;
        string nameCorresponding;
        foreach (string lineChartName in chartLineTypes)
        {
            nameCorresponding = chartLineTypesCode[iter_index];
            if (lineChartName == "Mana" || lineChartName == "Mana Speed")
            {
                iter_index += 1;
                continue;
            }

            iter_index += 1;

            if(dataFromMerge[nameCorresponding] != -1000f)
            {
                dataCurrentGame[lineChartName] += (dataFromMerge[nameCorresponding] + 1f); //non-negative
            }
            else
            {
                dataCurrentGame[lineChartName] = -1000f;
            }
            statsControllerExpanded.UpdateDataGeneric(lineChartName, dataCurrentGame[lineChartName]);

        }

        UpdateStatsScreen();

    }

    public void FlushCurrentGameData()
    {
        if(dataCurrentGame.ContainsKey("Physical: Visit All Slots") == false)
        {
            foreach (string lineChartName in chartLineTypes)
            {
                dataCurrentGame.Add(lineChartName, 0f);
            }
        }
        else
        {
            foreach (string lineChartName in chartLineTypes)
            {
                dataCurrentGame[lineChartName] = 0f;
            }
        }

        statsControllerExpanded = StatsControllerExpanded.Instance;
        statsControllerExpanded.FlushCurrentGameData();
    }

}
