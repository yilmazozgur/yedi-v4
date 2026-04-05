using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using System;
using UnityEngine.UI;

using BayatGames.SaveGameFree;

public class SevenMinuteController : MonoBehaviour
{
    string[] gamesList = { "Math", "Visual", "Spatial", "Verbal",
        "Music", "Memory", "Physical" };
    string[] mathGameList = { "Math: Add", "Math: Multiply", "Math: Coprimes",
        "Math: Vector", "Math: Interval", "Math: Trigonometry", "Math: Sort" };
    string[] mathGameListCode = { "add", "multiply", "gcd", "vector",
        "interval", "trigon", "sort" };
    string[] visualGameList = { "Visual: Add", "Visual: Subtract",
        "Visual: Gray", "Visual: Text" };
    string[] visualGameListCode = { "add", "subtract", "gray", "text" };
    string[] spatialGameList = { "Spatial: Triangle", "Spatial: Rectangle",
        "Spatial: 3 Shapes", "Spatial: Kanizsa", "Spatial: Angle",
        "Spatial: Hanoi" };
    string[] spatialGameListCode = { "triangle", "rectangle", "triple",
        "kanizsa", "sphere", "hanoi" };
    string[] verbalGameList = { "Verbal: Antonym Verbs", "Verbal: Antonym Adjectives",
        "Verbal: Antonym Nouns", "Verbal: Synonym Verbs", "Verbal: Synonym Adjectives",
        "Verbal: Grammar", "Verbal: Question Answer", "Verbal: Generate Words" };
    string[] verbalGameListCode = { "verbs", "adjectives", "nouns",
        "synVerbs", "synAdjectives",
        "grammar", "questions", "scrabble" };
    string[] musicGameList = {"Music: Double Slow", "Music: Single Slow",
        "Music: Double Fast", "Music: Single Fast", "Music: Tik and Tok",
        "Music: 5 Slots"};
    string[] musicGameListCode = { "double", "single", "double fast",
        "single fast", "tiktok", "five" };
    string[] memoryGameList = { "Memory: Easy", "Memory: Moderate", "Memory: Hard" };
    string[] memoryGameListCode = { "every action", "show all", "show one" };
    string[] physicalGameList = { "Physical: Fast and Accurate" ,
        "Physical: Visit the Bank", "Physical: Visit All Slots" };
    string[] physicalGameListCode = { "speed accuracy", "speed accuracy halfway",
        "visit all slots" };

    WorkoutProgressBar workoutProgressBar;
    WorkoutNextGameName workoutNextGameName;
    HeptagonController heptagonController;
    Text textNextGame;

    DateTime nowIs;
    DateTime initializedAt;
    bool workoutInitialized;
    bool[] gamesPlayed = new bool[5]{ false, false, false, false, false };
    string[] game1Modes = { "none", "none", "none", "none", "none", "none", "none" };
    string[] game2Modes = { "none", "none", "none", "none", "none", "none", "none" };
    string[] game3Modes = { "none", "none", "none", "none", "none", "none", "none" };
    string[] game4Modes = { "none", "none", "none", "none", "none", "none", "none" };
    string[] game5Modes = { "none", "none", "none", "none", "none", "none", "none" };
    string game1Name;
    string game2Name;
    string game3Name;
    string game4Name;
    string game5Name;
    List<string[]> gameModesAll;
    List<string> gameNamesAll;
    int currentGameIndex;
    float percentPlayed = 0f;
    bool justInitialized = false;


    private void SaveGameData()
    {
        SaveGame.Save<bool>("workoutInitialized", workoutInitialized);
        SaveGame.Save<DateTime>("initializedAt", nowIs);
        SaveGame.Save<List<string[]>>("gameModesAll", gameModesAll);
        SaveGame.Save<List<string>>("gameNamesAll", gameNamesAll);
    }

    private void LoadSavedData()
    {
        workoutInitialized = SaveGame.Load<bool>("workoutInitialized");
        initializedAt = SaveGame.Load<DateTime>("initializedAt");
        gameModesAll = SaveGame.Load<List<string[]>>("gameModesAll");
        gameNamesAll = SaveGame.Load<List<string>>("gameNamesAll");
        currentGameIndex = SaveGame.Load<int>("currentGameIndex");

    }

    public void gamePlayed()
    {
        currentGameIndex = SaveGame.Load<int>("currentGameIndex");
        currentGameIndex += 1;
        SaveGame.Save<int>("currentGameIndex", currentGameIndex);
    }

    public void LoadNextGame()
    {

        workoutProgressBar = FindAnyObjectByType<WorkoutProgressBar>();
        workoutNextGameName = FindAnyObjectByType<WorkoutNextGameName>();
        heptagonController = FindAnyObjectByType<HeptagonController>();
        textNextGame = workoutNextGameName.GetComponent<Text>();

        if (SaveGame.Exists("workoutInitialized"))
        {
            LoadSavedData();
        }
        else
        {
            workoutInitialized = false;
        }

        nowIs = DateTime.Now;

        //workoutInitialized = false;

        if (workoutInitialized == false || currentGameIndex >= 5)
        {
            Debug.Log("Generating 5 games");
            GenerateFiveGames();
            ResetGamesPlayed();
            workoutInitialized = true;
            SaveGameData();
            justInitialized = true;
        }
        else
        {
            justInitialized = false;
        }

        string[] modeList = gameModesAll[currentGameIndex];

        AdjustGameNameText();

        SaveGameWorkout(modeList[0], modeList[1], modeList[2], modeList[3],
            modeList[4], modeList[5], modeList[6]);
        heptagonController.validSelection = true;
        heptagonController.WorkoutHeptagonInfo(modeList[0], modeList[1],
            modeList[2], modeList[3], modeList[4], modeList[5], modeList[6]);

        StartCoroutine(AdjustProgressWheel());
    }

    IEnumerator AdjustProgressWheel()
    {
        percentPlayed = 100f * (currentGameIndex / 5f);
        yield return new WaitForSeconds(0.2f);
        workoutProgressBar = FindAnyObjectByType<WorkoutProgressBar>();
        workoutProgressBar.AdjustSlider(percentPlayed, justInitialized);

    }

    private void AdjustGameNameText()
    {
        string currentGameName = gameNamesAll[currentGameIndex];
        textNextGame.text = currentGameName;

    }

    private void ResetGamesPlayed()
    {
        currentGameIndex = 0;
        SaveGame.Save<int>("currentGameIndex", currentGameIndex);
    }

    public void GenerateFiveGames()
    {
        //Game 1: 2 of the first 4
        int randomIndex1Game1 = UnityEngine.Random.Range(0, 4);
        int randomIndex2Game1 = UnityEngine.Random.Range(0, 4);
        while (randomIndex2Game1 == randomIndex1Game1)
        {
            randomIndex2Game1 = UnityEngine.Random.Range(0, 4);
        }
        (string gameName1Game1, string gameName1CodeGame1, float gameNo1Game1)
            = RandomGameForCategory(randomIndex1Game1);
        (string gameName2Game1, string gameName2CodeGame1, float gameNo2Game1)
            = RandomGameForCategory(randomIndex2Game1);
        game1Modes = SetupGameModes(game1Modes, randomIndex1Game1, randomIndex2Game1,
            gameName1CodeGame1, gameName2CodeGame1);
        game1Name = gameName1Game1 + "\n" + "+" + "\n" + gameName2Game1;

        //Game 2: 2 of the first 4 (mutually exclusive from Game 1)
        int randomIndex1Game2 = UnityEngine.Random.Range(0, 4);
        while(randomIndex1Game2 == randomIndex1Game1 || randomIndex1Game2 == randomIndex2Game1)
        {
            randomIndex1Game2 = UnityEngine.Random.Range(0, 4);
        }
        int randomIndex2Game2 = UnityEngine.Random.Range(0, 4);
        while (randomIndex2Game2 == randomIndex1Game2 ||
            randomIndex2Game2 == randomIndex1Game1 || randomIndex2Game2 == randomIndex2Game1)
        {
            randomIndex2Game2 = UnityEngine.Random.Range(0, 4);
        }

        (string gameName1Game2, string gameName1CodeGame2, float gameNo1Game2)
            = RandomGameForCategory(randomIndex1Game2);
        (string gameName2Game2, string gameName2CodeGame2, float gameNo2Game2)
            = RandomGameForCategory(randomIndex2Game2);
        game2Modes = SetupGameModes(game2Modes, randomIndex1Game2, randomIndex2Game2,
            gameName1CodeGame2, gameName2CodeGame2);
        game2Name = gameName1Game2 + "\n" + "+" + "\n" + gameName2Game2;


        //Game 3: Music and 1 of the first 4
        int randomIndex1Game3 = 4;
        int randomIndex2Game3 = UnityEngine.Random.Range(0, 4);
        (string gameName1Game3, string gameName1CodeGame3, float gameNo1Game3)
            = RandomGameForCategory(randomIndex1Game3);
        (string gameName2Game3, string gameName2CodeGame3, float gameNo2Game3)
            = RandomGameForCategory(randomIndex2Game3);
        game3Modes = SetupGameModes(game3Modes, randomIndex1Game3, randomIndex2Game3,
            gameName1CodeGame3, gameName2CodeGame3);
        game3Name = gameName1Game3 + "\n" + "+" + "\n" + gameName2Game3;


        //Game 4: Memory and 1 of the first 4
        int randomIndex1Game4 = 5;
        int randomIndex2Game4 = UnityEngine.Random.Range(0, 4);
        (string gameName1Game4, string gameName1CodeGame4, float gameNo1Game4)
            = RandomGameForCategory(randomIndex1Game4);
        (string gameName2Game4, string gameName2CodeGame4, float gameNo2Game4)
            = RandomGameForCategory(randomIndex2Game4);
        game4Modes = SetupGameModes(game4Modes, randomIndex1Game4, randomIndex2Game4,
            gameName1CodeGame4, gameName2CodeGame4);
        game4Name = gameName1Game4 + "\n" + "+" + "\n" + gameName2Game4;


        //Game 5: Physical and 1 of the first 4
        int randomIndex1Game5 = 6;
        int randomIndex2Game5 = UnityEngine.Random.Range(0, 4);
        (string gameName1Game5, string gameName1CodeGame5, float gameNo1Game5)
            = RandomGameForCategory(randomIndex1Game5);
        (string gameName2Game5, string gameName2CodeGame5, float gameNo2Game5)
            = RandomGameForCategory(randomIndex2Game5);
        game5Modes = SetupGameModes(game5Modes, randomIndex1Game5, randomIndex2Game5,
            gameName1CodeGame5, gameName2CodeGame5);
        game5Name = gameName1Game5 + "\n" + "+" + "\n" + gameName2Game5;


        gameModesAll =  new List<string[]> { game1Modes, //game2Modes,
            game3Modes, game4Modes, game5Modes };
        gameNamesAll = new List<string> { game1Name, //game2Name,
            game3Name, game4Name, game5Name };
        SaveGame.Save<List<string[]>>("gameModesAll", gameModesAll);
        SaveGame.Save<List<string>>("gameNamesAll", gameNamesAll);
    }

    

    private string[] SetupGameModes(string[] gameModes, int randomIndex1, int randomIndex2,
        string gameName1CodeGame, string gameName2CodeGame)
    {

        gameModes[randomIndex1] = gameName1CodeGame;
        gameModes[randomIndex2] = gameName2CodeGame;

        return gameModes;

        
    }

    private void SaveGameWorkout(string modeNumber, string modeColor,
        string modeShape, string modeWord, string modeBeat, string modeMemory,
        string modeMotor)
    {
        SaveGame.Save<string>("modeNumber", modeNumber);
        SaveGame.Save<string>("modeColor", modeColor);
        SaveGame.Save<string>("modeShape", modeShape);
        SaveGame.Save<string>("modeWord", modeWord);
        SaveGame.Save<string>("modeBeat", modeBeat);
        SaveGame.Save<string>("modeMemory", modeMemory);
        SaveGame.Save<string>("modeMotor", modeMotor);
    }


    private (string, string, float) RandomGameForCategory(int categoryIndex)
    {
        string[] gameListQuery;
        string[] gameListQueryCode;
        float gameMultiplier;

        if (categoryIndex == 0)
        {
            gameListQuery = mathGameList;
            gameListQueryCode = mathGameListCode;
            gameMultiplier = 1000000;
        }
        else if(categoryIndex == 1)
        {
            gameListQuery = visualGameList;
            gameListQueryCode = visualGameListCode;
            gameMultiplier = 100000;
        }
        else if (categoryIndex == 2)
        {
            gameListQuery = spatialGameList;
            gameListQueryCode = spatialGameListCode;
            gameMultiplier = 10000;
        }
        else if (categoryIndex == 3)
        {
            gameListQuery = verbalGameList;
            gameListQueryCode = verbalGameListCode;
            gameMultiplier = 1000;
        }
        else if (categoryIndex == 4)
        {
            gameListQuery = musicGameList;
            gameListQueryCode = musicGameListCode;
            gameMultiplier = 100;
        }
        else if (categoryIndex == 5)
        {
            gameListQuery = memoryGameList;
            gameListQueryCode = memoryGameListCode;
            gameMultiplier = 10;
        }
        else
        {
            gameListQuery = physicalGameList;
            gameListQueryCode = physicalGameListCode;
            gameMultiplier = 1;
        }

        int randomIndex = UnityEngine.Random.Range(0, gameListQuery.Length);
        string gameName = gameListQuery[randomIndex];
        string gameNameCode = gameListQueryCode[randomIndex];
        float gameNumber = gameMultiplier + randomIndex * gameMultiplier;

        return (gameName, gameNameCode, gameNumber);
    }



    //else
    //{
    //    TimeSpan ts = initializedAt - nowIs;
    //    double totalMinutes = ts.TotalMinutes;
    //    if(totalMinutes > 1440d)
    //    {
    //        GenerateFiveGames();
    //        ResetGamesPlayed();
    //        workoutInitialized = true;
    //        SaveGame.Save<bool>("workoutInitialized", workoutInitialized);
    //        SaveGame.Save<DateTime>("initializedAt", nowIs);
    //    }
    //}


}
