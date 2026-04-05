using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class ManaDisplay : MonoBehaviour
{
    public float baseMana = 200;
    [SerializeField] float timeManaDiv = 5f;
    public float manaValue;
    public float manaValueMax;
    float manaValueRounded;
    Text manaText;
    bool triggeredLevelFinished = false;
    float timeManaCost;
    float timeManaCostCumulative = 0;
    float levelTimer;
    float difficulty;
    public float manaPerTime = 0;
    public float manaPerTimeMax = 0;
    public float manaReductionMultiplier;
    public float manaIncreaseMultiplier1;
    public float manaIncreaseMultiplier2;
    public float manaIncreaseMultiplier3;
    public float cardDrawThreshold;
    public int maxNumberOfMerges;
    StatsCollectorExpanded statsCollectorExpanded;
    LevelController levelController;
    GameTimer gameTimer;

    void Start()
    {
        baseMana = 200f;
        levelController = FindObjectOfType<LevelController>();
        gameTimer = FindObjectOfType<GameTimer>();
        difficulty = 0f;
        //difficulty = PlayerPrefsController.GetDifficulty();
        manaValue = baseMana - difficulty * 50f;
        

        if (difficulty == 0)
        {
            manaReductionMultiplier = 0.9f; //0.9f
            manaIncreaseMultiplier1 = 1.5f; //1.5f
            manaIncreaseMultiplier2 = 2f; //2f
            manaIncreaseMultiplier3 = 2.5f; //3f
            cardDrawThreshold = 100;
            maxNumberOfMerges = 3;
        }
        else if(difficulty == 1)
        {
            manaReductionMultiplier = 0.8f;
            manaIncreaseMultiplier1 = 1.2f;
            manaIncreaseMultiplier2 = 1.5f;
            manaIncreaseMultiplier3 = 2f;
            cardDrawThreshold = 200;
            maxNumberOfMerges = 4;
        }
        else if (difficulty == 2)
        {
            manaReductionMultiplier = 0.7f;
            manaIncreaseMultiplier1 = 1.1f;
            manaIncreaseMultiplier2 = 1.3f;
            manaIncreaseMultiplier3 = 1.7f;
            cardDrawThreshold = 400;
            maxNumberOfMerges = 5;
        }

        manaText = GetComponent<Text>();
        levelTimer = Time.timeSinceLevelLoad;
        UpdateDisplay();

        statsCollectorExpanded = FindObjectOfType<StatsCollectorExpanded>();
        //AddMana(0f);
        //statsCollectorExpanded.UpdateMaxManaValue(manaValue);
    }

    void Update()
    {
        if (triggeredLevelFinished) { return; }
        timeManaCost = (Time.timeSinceLevelLoad - levelTimer) / timeManaDiv;
        timeManaCostCumulative += timeManaCost;
        levelTimer = Time.timeSinceLevelLoad;
        if (timeManaCostCumulative >= 1)
        {
            SpendMana(timeManaCostCumulative);
            timeManaCostCumulative = 0;
        }
        manaPerTime = Mathf.Max((difficulty + 1) * (manaValue - baseMana) /
            Time.timeSinceLevelLoad, 0);
        if (manaPerTime > manaPerTimeMax)
        {
            manaPerTimeMax = manaPerTime;
            statsCollectorExpanded.UpdateMaxManaPerTime(manaPerTimeMax);
        }

    }

    private void UpdateDisplay()
    {
        if (gameTimer.ReturnTimerFinished() == false)
        {
            manaValueRounded = Mathf.Round(manaValue);
            if(manaText)
            {
                manaText.text = manaValueRounded.ToString();
            }
        }
    }

    public bool HaveEnoughMana(float amount)
    {
        return manaValue >= amount + 1f;
    }

    public void AddMana(float amount)
    {
        manaValue += amount;
        UpdateDisplay();
        if(manaValue > manaValueMax)
        {
            manaValueMax = manaValue;
            statsCollectorExpanded.UpdateMaxManaValue(manaValueMax);
        }
    }

    public void SpendMana(float cost)
    {
        manaValue -= cost;
        manaValue = Mathf.Max(manaValue, 0f);
        UpdateDisplay();

        if (manaValue <= 0)
        {
            triggeredLevelFinished = true;
            levelController.gameFinished = true;
            levelController.LevelTimerFinished();
        }
    }
}
