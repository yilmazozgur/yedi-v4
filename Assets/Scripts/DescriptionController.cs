using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class DescriptionController : MonoBehaviour
{
    GameDescription[] gameDescriptions;
    GameInfo gameInfo;
    MainCanvas mainCanvas;
    //GameDescription numberAdd;
    //GameDescription colorAdd;
    Canvas numberAdd;
    Canvas colorAdd;
    Canvas shapeTriangle;
    Canvas wordVerbs;
    Canvas beatDouble;
    Canvas memoryEasy;
    Canvas memoryMedium;
    Canvas motorOnSlot;
    Canvas numberMultiply;
    Canvas numberGcd;
    Canvas numberVector;
    Canvas numberInterval;
    Canvas numberTrigon;
    Canvas numberSort;
    Canvas colorSubtract;
    Canvas colorGray;
    Canvas colorText;
    Canvas shapeRectangle;
    Canvas shapeTriple;
    Canvas shapeKanizsa;
    Canvas shapeSphere;
    Canvas shapeHanoi;
    Canvas wordAdjectives;
    Canvas wordPrepositions;
    Canvas wordNouns;
    Canvas wordSymVerbs;
    Canvas wordSymAdjectives;
    Canvas wordGrammar;
    Canvas wordQuestions;
    Canvas wordScrabble;
    Canvas beatSingle;
    Canvas beatDoubleFast;
    Canvas beatSingleFast;
    Canvas beatTikTok;
    Canvas beatFive;
    Canvas memoryHard;
    Canvas motorHalfwaySlot;
    Canvas motorVisitAll;
    Canvas anyCombination;
    Canvas tutorial;
    Canvas workout;

    bool initialized = false;

    // Start is called before the first frame update
    void Start()
    {
        gameInfo = FindObjectOfType<GameInfo>();

        mainCanvas = FindObjectOfType<MainCanvas>();

        FindAllGameDescriptions();

        if (mainCanvas != null)
        {
            gameInfo.enabled = false;
            DeactivateAllDescriptions();
        }
  
    }

    public void FindAllGameDescriptions()
    {
        if(initialized == false)
        {
            gameDescriptions = FindObjectsOfType<GameDescription>();
            foreach (GameDescription gameDescription in gameDescriptions)
            {
                if (gameDescription.gameObject.name == "Game Description Add Number Canvas")
                {
                    numberAdd = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Add Color Canvas")
                {
                    colorAdd = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Triangle Shape Canvas")
                {
                    shapeTriangle = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Verb Word Canvas")
                {
                    wordVerbs = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Double Beat Canvas")
                {
                    beatDouble = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Easy Memory Canvas")
                {
                    memoryEasy = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Medium Memory Canvas")
                {
                    memoryMedium = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description OnSlot Motor Canvas")
                {
                    motorOnSlot = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Multiply Number Canvas")
                {
                    numberMultiply = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Gcd Number Canvas")
                {
                    numberGcd = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Vector Number Canvas")
                {
                    numberVector = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Interval Number Canvas")
                {
                    numberInterval = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Trigon Number Canvas")
                {
                    numberTrigon = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Sort Number Canvas")
                {
                    numberSort = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Subtract Color Canvas")
                {
                    colorSubtract = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Gray Color Canvas")
                {
                    colorGray = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Text Color Canvas")
                {
                    colorText = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Rectangle Shape Canvas")
                {
                    shapeRectangle = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Triple Shape Canvas")
                {
                    shapeTriple = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Kanizsa Shape Canvas")
                {
                    shapeKanizsa = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Sphere Shape Canvas")
                {
                    shapeSphere = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Hanoi Shape Canvas")
                {
                    shapeHanoi = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Adjective Word Canvas")
                {
                    wordAdjectives = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Preposition Word Canvas")
                {
                    wordPrepositions = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Noun Word Canvas")
                {
                    wordNouns = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description SynVerb Word Canvas")
                {
                    wordSymVerbs = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description SynAdjective Word Canvas")
                {
                    wordSymAdjectives = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Grammar Word Canvas")
                {
                    wordGrammar = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Question Word Canvas")
                {
                    wordQuestions = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Scrabble Word Canvas")
                {
                    wordScrabble = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Single Beat Canvas")
                {
                    beatSingle = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Double Fast Beat Canvas")
                {
                    beatDoubleFast = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Single Fast Beat Canvas")
                {
                    beatSingleFast = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description TikTok Beat Canvas")
                {
                    beatTikTok = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Five Beat Canvas")
                {
                    beatFive = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Hard Memory Canvas")
                {
                    memoryHard = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description HalfwaySlot Motor Canvas")
                {
                    motorHalfwaySlot = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description VisitAll Motor Canvas")
                {
                    motorVisitAll = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Any Combination Canvas")
                {
                    anyCombination = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Tutorial Canvas")
                {
                    tutorial = gameDescription.GetComponentInParent<Canvas>();
                }
                if (gameDescription.gameObject.name == "Game Description Workout Canvas")
                {
                    workout = gameDescription.GetComponentInParent<Canvas>();
                }
            }
        }
        
        //initialized = true;
    }

    public void DeactivateAllDescriptions()
    {
        FindAllGameDescriptions();
        numberAdd.gameObject.SetActive(false);
        colorAdd.gameObject.SetActive(false);
        shapeTriangle.gameObject.SetActive(false);
        wordVerbs.gameObject.SetActive(false);
        beatDouble.gameObject.SetActive(false);
        memoryEasy.gameObject.SetActive(false);
        memoryMedium.gameObject.SetActive(false);
        motorOnSlot.gameObject.SetActive(false);

        numberMultiply.gameObject.SetActive(false);
        numberGcd.gameObject.SetActive(false);
        numberVector.gameObject.SetActive(false);
        numberInterval.gameObject.SetActive(false);
        numberTrigon.gameObject.SetActive(false);
        numberSort.gameObject.SetActive(false);
        colorSubtract.gameObject.SetActive(false);
        colorGray.gameObject.SetActive(false);
        colorText.gameObject.SetActive(false);
        shapeRectangle.gameObject.SetActive(false);
        shapeTriple.gameObject.SetActive(false);
        shapeKanizsa.gameObject.SetActive(false);
        shapeSphere.gameObject.SetActive(false);
        shapeHanoi.gameObject.SetActive(false);
        wordAdjectives.gameObject.SetActive(false);
        wordPrepositions.gameObject.SetActive(false);
        wordNouns.gameObject.SetActive(false);
        wordSymVerbs.gameObject.SetActive(false);
        wordSymAdjectives.gameObject.SetActive(false);
        wordGrammar.gameObject.SetActive(false);
        wordQuestions.gameObject.SetActive(false);
        wordScrabble.gameObject.SetActive(false);
        beatSingle.gameObject.SetActive(false);
        beatDoubleFast.gameObject.SetActive(false);
        beatSingleFast.gameObject.SetActive(false);
        beatTikTok.gameObject.SetActive(false);
        beatFive.gameObject.SetActive(false);
        memoryHard.gameObject.SetActive(false);
        motorHalfwaySlot.gameObject.SetActive(false);
        motorVisitAll.gameObject.SetActive(false);

        anyCombination.gameObject.SetActive(false);
        tutorial.gameObject.SetActive(false);
        workout.gameObject.SetActive(false);

    }

    public void HideDescriptions()
    {
        DeactivateAllDescriptions();
    }

    public void SetAddNumberDescription()
    {
        DeactivateAllDescriptions();
        numberAdd.gameObject.SetActive(true);
    }

    public void SetMultiplyNumberDescription()
    {
        DeactivateAllDescriptions();
        numberMultiply.gameObject.SetActive(true);
    }

    public void SetGcdNumberDescription()
    {
        DeactivateAllDescriptions();
        numberGcd.gameObject.SetActive(true);
    }

    public void SetVectoreNumberDescription()
    {
        DeactivateAllDescriptions();
        numberVector.gameObject.SetActive(true);
    }

    public void SetIntervalNumberDescription()
    {
        DeactivateAllDescriptions();
        numberInterval.gameObject.SetActive(true);
    }

    public void SetTrigonNumberDescription()
    {
        DeactivateAllDescriptions();
        numberTrigon.gameObject.SetActive(true);
    }

    public void SetSortNumberDescription()
    {
        DeactivateAllDescriptions();
        numberSort.gameObject.SetActive(true);
    }

    public void SetAddColorDescription()
    {
        DeactivateAllDescriptions();
        colorAdd.gameObject.SetActive(true);
    }

    public void SetSubtractColorDescription()
    {
        DeactivateAllDescriptions();
        colorSubtract.gameObject.SetActive(true);
    }

    public void SetGrayColorDescription()
    {
        DeactivateAllDescriptions();
        colorGray.gameObject.SetActive(true);
    }

    public void SetTextColorDescription()
    {
        DeactivateAllDescriptions();
        colorText.gameObject.SetActive(true);
    }

    public void SetShapeTriangleDescription()
    {
        DeactivateAllDescriptions();
        shapeTriangle.gameObject.SetActive(true);
    }

    public void SetShapeSquareDescription()
    {
        DeactivateAllDescriptions();
        shapeRectangle.gameObject.SetActive(true);
    }

    public void SetShapeTripleDescription()
    {
        DeactivateAllDescriptions();
        shapeTriple.gameObject.SetActive(true);
    }

    public void SetShapeKanizsaDescription()
    {
        DeactivateAllDescriptions();
        shapeKanizsa.gameObject.SetActive(true);
    }

    public void SetShapeSphereDescription()
    {
        DeactivateAllDescriptions();
        shapeSphere.gameObject.SetActive(true);
    }

    public void SetShapeHanoiDescription()
    {
        DeactivateAllDescriptions();
        shapeHanoi.gameObject.SetActive(true);
    }

    public void SetSubtractVerbsDescription()
    {
        DeactivateAllDescriptions();
        wordVerbs.gameObject.SetActive(true);
    }

    public void SetSubtractAdjectivesDescription()
    {
        DeactivateAllDescriptions();
        wordAdjectives.gameObject.SetActive(true);
    }

    public void SetSubtractPrepositionsDescription()
    {
        DeactivateAllDescriptions();
        wordPrepositions.gameObject.SetActive(true);
    }

    public void SetSubtractNounsDescription()
    {
        DeactivateAllDescriptions();
        wordNouns.gameObject.SetActive(true);
    }

    public void SetSubtractSynVerbsDescription()
    {
        DeactivateAllDescriptions();
        wordSymVerbs.gameObject.SetActive(true);
    }

    public void SetSubtractSynAdjectivesDescription()
    {
        DeactivateAllDescriptions();
        wordSymAdjectives.gameObject.SetActive(true);
    }

    public void SetSubtractGrammarDescription()
    {
        DeactivateAllDescriptions();
        wordGrammar.gameObject.SetActive(true);
    }

    public void SetSubtractQuestionsDescription()
    {
        DeactivateAllDescriptions();
        wordQuestions.gameObject.SetActive(true);
    }

    public void SetScrabbleDescription()
    {
        DeactivateAllDescriptions();
        wordScrabble.gameObject.SetActive(true);
    }

    public void SetDoubleBeatDescription()
    {
        DeactivateAllDescriptions();
        beatDouble.gameObject.SetActive(true);
    }

    public void SetSingleBeatDescription()
    {
        DeactivateAllDescriptions();
        beatSingle.gameObject.SetActive(true);
    }

    public void SetDoubleFastBeatDescription()
    {
        DeactivateAllDescriptions();
        beatDoubleFast.gameObject.SetActive(true);
    }

    public void SetSingleFastBeatDescription()
    {
        DeactivateAllDescriptions();
        beatSingleFast.gameObject.SetActive(true);
    }

    public void SetTikTokBeatDescription()
    {
        DeactivateAllDescriptions();
        beatTikTok.gameObject.SetActive(true);
    }

    public void SetFiveBeatDescription()
    {
        DeactivateAllDescriptions();
        beatFive.gameObject.SetActive(true);
    }

    public void SetEasyMemoryDescription()
    {
        DeactivateAllDescriptions();
        memoryEasy.gameObject.SetActive(true);
    }

    public void SetMediumMemoryDescription()
    {
        DeactivateAllDescriptions();
        memoryMedium.gameObject.SetActive(true);
    }

    public void SetHardMemoryDescription()
    {
        DeactivateAllDescriptions();
        memoryHard.gameObject.SetActive(true);
    }

    public void SetOnSlotMotorDescription()
    {
        DeactivateAllDescriptions();
        motorOnSlot.gameObject.SetActive(true);
    }

    public void SetHalfwaySlotMotorDescription()
    {
        DeactivateAllDescriptions();
        motorHalfwaySlot.gameObject.SetActive(true);
    }

    public void SetVisitAllMotorDescription()
    {
        DeactivateAllDescriptions();
        motorVisitAll.gameObject.SetActive(true);
    }

    public void SetAnyCombinationDescription()
    {
        DeactivateAllDescriptions();
        anyCombination.gameObject.SetActive(true);
    }

    public void SetTutorialDescription()
    {
        DeactivateAllDescriptions();
        tutorial.gameObject.SetActive(true);
    }

    public void SetWorkoutDescription()
    {
        DeactivateAllDescriptions();
        workout.gameObject.SetActive(true);
    }

}
