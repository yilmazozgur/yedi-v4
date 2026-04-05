//using System.Collections;
//using System.Collections.Generic;
//using UnityEngine;
//using UnityEngine.UI;

//public class StatsCollector : MonoBehaviour
//{

//    public float manaValueMax = 0f;
//    public float manaPerTimeMax = 0f;
//    public float numberOfMerges = 0f;
//    public float numberGain = 0f;
//    public float colorGain = 0f;
//    public float shapeGain = 0f;
//    public float wordGain = 0f;
//    public float beatGain = 0f;
//    public float memoryGain = 0f;
//    public float motorGain = 0f;

//    StatsController statsController;
//    LevelController levelController;
//    Text gameResultManaText;
//    Text gameResultManaSpeedText;
//    Text gameResultMathText;
//    Text gameResultColorText;
//    Text gameResultSpatialText;
//    Text gameResultVerbalText;
//    Text gameResultMusicText;
//    Text gameResultMemoryText;
//    Text gameResultMotorText;
//    Text gameResultTitleTextMath;
//    Text gameResultTitleTextColor;
//    Text gameResultTitleTextSpatial;
//    Text gameResultTitleTextVerbal;
//    Text gameResultTitleTextMusic;
//    Text gameResultTitleTextMemory;
//    Text gameResultTitleTextMotor;

//    Color colorMathValueText;
//    Color colorMathTitleText;
//    Color colorColorValueText;
//    Color colorColorTitleText;
//    Color colorSpatialValueText;
//    Color colorSpatialTitleText;
//    Color colorVerbalValueText;
//    Color colorVerbalTitleText;
//    Color colorMusicValueText;
//    Color colorMusicTitleText;
//    Color colorMemoryValueText;
//    Color colorMemoryTitleText;
//    Color colorMotorValueText;
//    Color colorMotorTitleText;

//    void Start()
//    {
//        statsController = FindAnyObjectByType<StatsController>();
//        levelController = FindAnyObjectByType<LevelController>();
//        gameResultManaText = FindAnyObjectByType<GameResultMana>().GetComponent<Text>();
//        gameResultManaSpeedText = FindAnyObjectByType<GameResultManaSpeed>().GetComponent<Text>();
//        gameResultMathText = FindAnyObjectByType<GameResultMath>().GetComponent<Text>();
//        gameResultColorText = FindAnyObjectByType<GameResultColor>().GetComponent<Text>();
//        gameResultSpatialText = FindAnyObjectByType<GameResultSpatial>().GetComponent<Text>();
//        gameResultVerbalText = FindAnyObjectByType<GameResultVerbal>().GetComponent<Text>();
//        gameResultMusicText = FindAnyObjectByType<GameResultMusic>().GetComponent<Text>();
//        gameResultMemoryText = FindAnyObjectByType<GameResultMemory>().GetComponent<Text>();
//        gameResultMotorText = FindAnyObjectByType<GameResultMotor>().GetComponent<Text>();

//        gameResultTitleTextMath = FindAnyObjectByType<GameResultMath>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
//        gameResultTitleTextColor = FindAnyObjectByType<GameResultColor>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
//        gameResultTitleTextSpatial = FindAnyObjectByType<GameResultSpatial>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
//        gameResultTitleTextVerbal = FindAnyObjectByType<GameResultVerbal>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
//        gameResultTitleTextMusic = FindAnyObjectByType<GameResultMusic>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
//        gameResultTitleTextMemory = FindAnyObjectByType<GameResultMemory>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();
//        gameResultTitleTextMotor = FindAnyObjectByType<GameResultMotor>().GetComponentInParent<GameResultTitle>().GetComponent<Text>();

//        colorMathValueText = gameResultMathText.color;
//        gameResultMathText.text = "---";
//        colorMathValueText.a = 0.1f;
//        gameResultMathText.color = colorMathValueText;
//        gameResultTitleTextMath.color = colorMathValueText;

//        colorColorValueText = gameResultColorText.color;
//        gameResultColorText.text = "---";
//        colorColorValueText.a = 0.1f;
//        gameResultColorText.color = colorColorValueText;
//        gameResultTitleTextColor.color = colorColorValueText;

//        colorSpatialValueText = gameResultSpatialText.color;
//        gameResultSpatialText.text = "---";
//        colorSpatialValueText.a = 0.1f;
//        gameResultSpatialText.color = colorSpatialValueText;
//        gameResultTitleTextSpatial.color = colorSpatialValueText;

//        colorVerbalValueText = gameResultVerbalText.color;
//        gameResultVerbalText.text = "---";
//        colorVerbalValueText.a = 0.1f;
//        gameResultVerbalText.color = colorVerbalValueText;
//        gameResultTitleTextVerbal.color = colorVerbalValueText;

//        colorMusicValueText = gameResultMusicText.color;
//        gameResultMusicText.text = "---";
//        colorMusicValueText.a = 0.1f;
//        gameResultMusicText.color = colorMusicValueText;
//        gameResultTitleTextMusic.color = colorMusicValueText;

//        colorMemoryValueText = gameResultMemoryText.color;
//        gameResultMemoryText.text = "---";
//        colorMemoryValueText.a = 0.1f;
//        gameResultMemoryText.color = colorMemoryValueText;
//        gameResultTitleTextMemory.color = colorMemoryValueText;

//        colorMotorValueText = gameResultMotorText.color;
//        gameResultMotorText.text = "---";
//        colorMotorValueText.a = 0.1f;
//        gameResultMotorText.color = colorMotorValueText;
//        gameResultTitleTextMotor.color = colorMotorValueText;

//        UpdateMaxManaValue(0f);
//        UpdateMaxManaPerTime(0f);
//        UpdateGains(0f, 0f, 0f, 0f, 0f, 0f, 0f);
//    }

//    public void UpdateMaxManaValue(float maxManaValueUpdate)
//    {
//        manaValueMax = maxManaValueUpdate;
//        statsController.UpdateMaxManaValue(manaValueMax);
//        if(gameResultManaText)
//        {
//            gameResultManaText.text = ((int)manaValueMax).ToString();
//        }
//    }

//    public float GetMaxManaValue()
//    {
//        return manaValueMax;
//    }

//    public void UpdateMaxManaPerTime(float maxmanaPerTimeUpdate)
//    {
//        manaPerTimeMax = maxmanaPerTimeUpdate;
//        statsController.UpdateMaxManaPerTime(manaPerTimeMax);
//        if(gameResultManaSpeedText)
//        {
//            gameResultManaSpeedText.text = ((int)manaPerTimeMax).ToString();
//        }
//    }

//    public float GetMaxManaPerTime()
//    {
//        return manaPerTimeMax;
//    }

//    public void UpdateNumberofMerges()
//    {
//        numberOfMerges++;
//        statsController.UpdateNumberofMerges(numberOfMerges);
//    }

//    public void UpdateGains(float numberGainUpdate, float colorGainUpdate,
//        float shapeGainUpdate, float wordGainUpdate, float beatGainUpdate,
//        float memoryGainUpdate, float motorGainUpdate)
//    {
//        numberGain += numberGainUpdate;
//        colorGain += colorGainUpdate;
//        shapeGain += shapeGainUpdate;
//        wordGain += wordGainUpdate;
//        beatGain += beatGainUpdate;
//        memoryGain += memoryGainUpdate;
//        motorGain += motorGainUpdate;

//        statsController.UpdateGains(numberGain, colorGain, shapeGain, wordGain, beatGain, memoryGain, motorGain);

//        float numberGainRanking = statsController.ApplyLogistic((numberGain / (numberOfMerges + 1)), statsController.avgPersonNumber, statsController.stdPersonNumber) - 1f;
//        float colorGainRanking = statsController.ApplyLogistic((colorGain / (numberOfMerges + 1)), statsController.avgPersonColor, statsController.stdPersonColor) - 1f;
//        float shapeGainRanking = statsController.ApplyLogistic((shapeGain / (numberOfMerges + 1)), statsController.avgPersonShape, statsController.stdPersonShape) - 1f;
//        float wordGainRanking = statsController.ApplyLogistic((wordGain / (numberOfMerges + 1)), statsController.avgPersonWord, statsController.stdPersonWord) - 1f;
//        float beatGainRanking = statsController.ApplyLogistic((beatGain / (numberOfMerges + 1)), statsController.avgPersonBeat, statsController.stdPersonBeat) - 1f;
//        float memoryGainRanking = statsController.ApplyLogistic((memoryGain / (numberOfMerges + 1)), statsController.avgPersonMemory, statsController.stdPersonMemory) - 1f;
//        float motorGainRanking = statsController.ApplyLogistic((motorGain / (numberOfMerges + 1)), statsController.avgPersonMotor, statsController.stdPersonMotor) - 1f;

//        if (levelController.numberActive)
//        {
//            colorMathValueText.a = 1f;
//            gameResultMathText.color = colorMathValueText;
//            gameResultTitleTextMath.color = colorMathValueText;
//            gameResultMathText.text = "%" + numberGainRanking.ToString() + " / ( " + (numberGain).ToString() + " )";
//        }


//        if (levelController.colorActive)
//        {
//            colorColorValueText.a = 1f;
//            gameResultColorText.color = colorColorValueText;
//            gameResultTitleTextColor.color = colorColorValueText;
//            gameResultColorText.text = "%" + colorGainRanking.ToString() + " / ( " + (colorGain).ToString() + " )";
//        }

//        if (levelController.shapeActive)
//        {
//            colorSpatialValueText.a = 1f;
//            gameResultSpatialText.color = colorSpatialValueText;
//            gameResultTitleTextSpatial.color = colorSpatialValueText;
//            gameResultSpatialText.text = "%" + shapeGainRanking.ToString() + " / ( " + (shapeGain).ToString() + " )";
//        }

//        if (levelController.wordActive)
//        {
//            colorVerbalValueText.a = 1f;
//            gameResultVerbalText.color = colorVerbalValueText;
//            gameResultTitleTextVerbal.color = colorVerbalValueText;
//            gameResultVerbalText.text = "%" + wordGainRanking.ToString() + " / ( " + (wordGain).ToString() + " )";
//        }

//        if (levelController.beatActive)
//        {
//            colorMusicValueText.a = 1f;
//            gameResultMusicText.color = colorMusicValueText;
//            gameResultTitleTextMusic.color = colorMusicValueText;
//            gameResultMusicText.text = "%" + beatGainRanking.ToString() + " / ( " + (beatGain).ToString() + " )";
//        }

//        if (levelController.memoryActive)
//        {
//            colorMemoryValueText.a = 1f;
//            gameResultMemoryText.color = colorMemoryValueText;
//            gameResultTitleTextMemory.color = colorMemoryValueText;
//            gameResultMemoryText.text = "%" + memoryGainRanking.ToString() + " / ( " + (memoryGain).ToString() + " )";
//        }

//        if (levelController.motorActive)
//        {
//            colorMotorValueText.a = 1f;
//            gameResultMotorText.color = colorMotorValueText;
//            gameResultTitleTextMotor.color = colorMotorValueText;
//            gameResultMotorText.text = "%" + motorGainRanking.ToString() + " / ( " + (motorGain).ToString() + " )";
//        }

//    }

//}
