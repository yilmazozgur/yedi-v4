using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class ManaPerTime : MonoBehaviour
{
    float manaPerTimevalue;
    Text manaPerTimeText;
    float manaValueRounded;
    ManaDisplay manaDisplay;
    LevelController levelController;
 
    void Start()
    {
        manaPerTimeText = GetComponent<Text>();
        manaDisplay = ManaDisplay.Instance;
        manaPerTimevalue = 0;
        levelController = LevelController.Instance;
        UpdateDisplay();
    }

    void Update()
    {
        if(levelController.gameFinished == false)
        {
            manaPerTimevalue = manaDisplay.manaPerTimeMax;
            UpdateDisplay();
        }
    }

    private void UpdateDisplay()
    {
        manaValueRounded = Mathf.Round(manaPerTimevalue);
        manaPerTimeText.text = manaValueRounded.ToString() + "  /sec";
    } 
}
