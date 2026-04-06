using UnityEngine;

public class ScoreManager : MonoBehaviour
{
    public static ScoreManager Instance { get; private set; }

    public static string playerName = "default";
    public static string currentConfigKey = "";
    public static int currentMaxScore = 0;

    void Awake()
    {
        Instance = this;
    }

    void Start()
    {
        playerName = StatsSyncBridge.GetPlayerName();
        currentConfigKey = BuildConfigKey();
        Debug.Log("ScoreManager: player=" + playerName + " config=" + currentConfigKey);

        if (!string.IsNullOrEmpty(currentConfigKey))
        {
            currentMaxScore = StatsSyncBridge.GetMaxScore(playerName, currentConfigKey);
            Debug.Log("ScoreManager: max score=" + currentMaxScore);
        }
    }

    public void OnGameEnd()
    {
        ManaDisplay manaDisplay = ManaDisplay.Instance;
        if (manaDisplay == null || string.IsNullOrEmpty(currentConfigKey)) return;

        int finalMana = (int)manaDisplay.manaValueMax;
        Debug.Log("ScoreManager.OnGameEnd: mana=" + finalMana + " config=" + currentConfigKey);

        int serverMax = StatsSyncBridge.PostScore(playerName, currentConfigKey, finalMana);
        if (serverMax > currentMaxScore)
            currentMaxScore = serverMax;
    }

    public static string BuildConfigKey()
    {
        var parts = new System.Collections.Generic.List<string>();

        if (!string.IsNullOrEmpty(HeptagonController.modeNumber))
            parts.Add("math:" + HeptagonController.modeNumber);
        if (!string.IsNullOrEmpty(HeptagonController.modeColor))
            parts.Add("visual:" + HeptagonController.modeColor);
        if (!string.IsNullOrEmpty(HeptagonController.modeShape))
            parts.Add("spatial:" + HeptagonController.modeShape);
        if (!string.IsNullOrEmpty(HeptagonController.modeWord))
            parts.Add("verbal:" + HeptagonController.modeWord);
        if (!string.IsNullOrEmpty(HeptagonController.modeBeat))
            parts.Add("music:" + HeptagonController.modeBeat);
        if (!string.IsNullOrEmpty(HeptagonController.modeMemory))
            parts.Add("memory:" + HeptagonController.modeMemory);
        if (!string.IsNullOrEmpty(HeptagonController.modeMotor))
            parts.Add("motor:" + HeptagonController.modeMotor);

        parts.Sort();
        return string.Join("+", parts);
    }
}
