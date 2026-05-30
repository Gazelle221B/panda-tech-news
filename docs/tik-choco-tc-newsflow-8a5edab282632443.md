# tik-choco-tc-newsflow Code Dump

## Directory Structure

```text
└── tik-choco-tc-newsflow/
    ├── README.md
    ├── go.mod
    ├── go.sum
    ├── cmd/
    │   └── news/
    │       ├── main.go
    │       └── main_test.go
    └── internal/
        ├── rssflow/
        │   ├── config.go
        │   ├── config_test.go
        │   ├── dedupe.go
        │   ├── dedupe_test.go
        │   ├── developer_news_fallback.go
        │   ├── developer_news_input.go
        │   ├── developer_news_rank.go
        │   ├── developer_news_script.go
        │   ├── openai.go
        │   ├── openai_prompts.go
        │   ├── openai_test.go
        │   ├── rss.go
        │   ├── rss_test.go
        │   ├── runner.go
        │   ├── sources.go
        │   └── sources_test.go
        └── tui/
            ├── model.go
            ├── views.go
            └── views_test.go

```

## FILE: README.md

````markdown
[Binary file]
````

## FILE: go.mod

```text
module github.com/tik-choco/rssflow

go 1.24.2

require (
    github.com/atotto/clipboard v0.1.4
    github.com/aymanbagabas/go-osc52/v2 v2.0.1
    github.com/charmbracelet/bubbles v1.0.0
    github.com/charmbracelet/bubbletea v1.3.10
    github.com/charmbracelet/lipgloss v1.1.0
    gopkg.in/yaml.v3 v3.0.1
)

require (
    github.com/charmbracelet/colorprofile v0.4.1 // indirect
    github.com/charmbracelet/x/ansi v0.11.6 // indirect
    github.com/charmbracelet/x/cellbuf v0.0.15 // indirect
    github.com/charmbracelet/x/term v0.2.2 // indirect
    github.com/clipperhouse/displaywidth v0.9.0 // indirect
    github.com/clipperhouse/stringish v0.1.1 // indirect
    github.com/clipperhouse/uax29/v2 v2.5.0 // indirect
    github.com/erikgeiser/coninput v0.0.0-20211004153227-1c3628e74d0f // indirect
    github.com/lucasb-eyer/go-colorful v1.3.0 // indirect
    github.com/mattn/go-isatty v0.0.20 // indirect
    github.com/mattn/go-localereader v0.0.1 // indirect
    github.com/mattn/go-runewidth v0.0.19 // indirect
    github.com/muesli/ansi v0.0.0-20230316100256-276c6243b2f6 // indirect
    github.com/muesli/cancelreader v0.2.2 // indirect
    github.com/muesli/termenv v0.16.0 // indirect
    github.com/rivo/uniseg v0.4.7 // indirect
    github.com/xo/terminfo v0.0.0-20220910002029-abceb7e1c41e // indirect
    golang.org/x/sys v0.38.0 // indirect
    golang.org/x/text v0.3.8 // indirect
)
```

## FILE: go.sum

```text
github.com/atotto/clipboard v0.1.4 h1:EH0zSVneZPSuFR11BlR9YppQTVDbh5+16AmcJi4g1z4=
github.com/atotto/clipboard v0.1.4/go.mod h1:ZY9tmq7sm5xIbd9bOK4onWV4S6X0u6GY7Vn0Yu86PYI=
github.com/aymanbagabas/go-osc52/v2 v2.0.1 h1:HwpRHbFMcZLEVr42D4p7XBqjyuxQH5SMiErDT4WkJ2k=
github.com/aymanbagabas/go-osc52/v2 v2.0.1/go.mod h1:uYgXzlJ7ZpABp8OJ+exZzJJhRNQ2ASbcXHWsFqH8hp8=
github.com/charmbracelet/bubbles v1.0.0 h1:12J8/ak/uCZEMQ6KU7pcfwceyjLlWsDLAxB5fXonfvc=
github.com/charmbracelet/bubbles v1.0.0/go.mod h1:9d/Zd5GdnauMI5ivUIVisuEm3ave1XwXtD1ckyV6r3E=
github.com/charmbracelet/bubbletea v1.3.10 h1:otUDHWMMzQSB0Pkc87rm691KZ3SWa4KUlvF9nRvCICw=
github.com/charmbracelet/bubbletea v1.3.10/go.mod h1:ORQfo0fk8U+po9VaNvnV95UPWA1BitP1E0N6xJPlHr4=
github.com/charmbracelet/colorprofile v0.4.1 h1:a1lO03qTrSIRaK8c3JRxJDZOvhvIeSco3ej+ngLk1kk=
github.com/charmbracelet/colorprofile v0.4.1/go.mod h1:U1d9Dljmdf9DLegaJ0nGZNJvoXAhayhmidOdcBwAvKk=
github.com/charmbracelet/lipgloss v1.1.0 h1:vYXsiLHVkK7fp74RkV7b2kq9+zDLoEU4MZoFqR/noCY=
github.com/charmbracelet/lipgloss v1.1.0/go.mod h1:/6Q8FR2o+kj8rz4Dq0zQc3vYf7X+B0binUUBwA0aL30=
github.com/charmbracelet/x/ansi v0.11.6 h1:GhV21SiDz/45W9AnV2R61xZMRri5NlLnl6CVF7ihZW8=
github.com/charmbracelet/x/ansi v0.11.6/go.mod h1:2JNYLgQUsyqaiLovhU2Rv/pb8r6ydXKS3NIttu3VGZQ=
github.com/charmbracelet/x/cellbuf v0.0.15 h1:ur3pZy0o6z/R7EylET877CBxaiE1Sp1GMxoFPAIztPI=
github.com/charmbracelet/x/cellbuf v0.0.15/go.mod h1:J1YVbR7MUuEGIFPCaaZ96KDl5NoS0DAWkskup+mOY+Q=
github.com/charmbracelet/x/term v0.2.2 h1:xVRT/S2ZcKdhhOuSP4t5cLi5o+JxklsoEObBSgfgZRk=
github.com/charmbracelet/x/term v0.2.2/go.mod h1:kF8CY5RddLWrsgVwpw4kAa6TESp6EB5y3uxGLeCqzAI=
github.com/clipperhouse/displaywidth v0.9.0 h1:Qb4KOhYwRiN3viMv1v/3cTBlz3AcAZX3+y9OLhMtAtA=
github.com/clipperhouse/displaywidth v0.9.0/go.mod h1:aCAAqTlh4GIVkhQnJpbL0T/WfcrJXHcj8C0yjYcjOZA=
github.com/clipperhouse/stringish v0.1.1 h1:+NSqMOr3GR6k1FdRhhnXrLfztGzuG+VuFDfatpWHKCs=
github.com/clipperhouse/stringish v0.1.1/go.mod h1:v/WhFtE1q0ovMta2+m+UbpZ+2/HEXNWYXQgCt4hdOzA=
github.com/clipperhouse/uax29/v2 v2.5.0 h1:x7T0T4eTHDONxFJsL94uKNKPHrclyFI0lm7+w94cO8U=
github.com/clipperhouse/uax29/v2 v2.5.0/go.mod h1:Wn1g7MK6OoeDT0vL+Q0SQLDz/KpfsVRgg6W7ihQeh4g=
github.com/erikgeiser/coninput v0.0.0-20211004153227-1c3628e74d0f h1:Y/CXytFA4m6baUTXGLOoWe4PQhGxaX0KpnayAqC48p4=
github.com/erikgeiser/coninput v0.0.0-20211004153227-1c3628e74d0f/go.mod h1:vw97MGsxSvLiUE2X8qFplwetxpGLQrlU1Q9AUEIzCaM=
github.com/lucasb-eyer/go-colorful v1.3.0 h1:2/yBRLdWBZKrf7gB40FoiKfAWYQ0lqNcbuQwVHXptag=
github.com/lucasb-eyer/go-colorful v1.3.0/go.mod h1:R4dSotOR9KMtayYi1e77YzuveK+i7ruzyGqttikkLy0=
github.com/mattn/go-isatty v0.0.20 h1:xfD0iDuEKnDkl03q4limB+vH+GxLEtL/jb4xVJSWWEY=
github.com/mattn/go-isatty v0.0.20/go.mod h1:W+V8PltTTMOvKvAeJH7IuucS94S2C6jfK/D7dTCTo3Y=
github.com/mattn/go-localereader v0.0.1 h1:ygSAOl7ZXTx4RdPYinUpg6W99U8jWvWi9Ye2JC/oIi4=
github.com/mattn/go-localereader v0.0.1/go.mod h1:8fBrzywKY7BI3czFoHkuzRoWE9C+EiG4R1k4Cjx5p88=
github.com/mattn/go-runewidth v0.0.19 h1:v++JhqYnZuu5jSKrk9RbgF5v4CGUjqRfBm05byFGLdw=
github.com/mattn/go-runewidth v0.0.19/go.mod h1:XBkDxAl56ILZc9knddidhrOlY5R/pDhgLpndooCuJAs=
github.com/muesli/ansi v0.0.0-20230316100256-276c6243b2f6 h1:ZK8zHtRHOkbHy6Mmr5D264iyp3TiX5OmNcI5cIARiQI=
github.com/muesli/ansi v0.0.0-20230316100256-276c6243b2f6/go.mod h1:CJlz5H+gyd6CUWT45Oy4q24RdLyn7Md9Vj2/ldJBSIo=
github.com/muesli/cancelreader v0.2.2 h1:3I4Kt4BQjOR54NavqnDogx/MIoWBFa0StPA8ELUXHmA=
github.com/muesli/cancelreader v0.2.2/go.mod h1:3XuTXfFS2VjM+HTLZY9Ak0l6eUKfijIfMUZ4EgX0QYo=
github.com/muesli/termenv v0.16.0 h1:S5AlUN9dENB57rsbnkPyfdGuWIlkmzJjbFf0Tf5FWUc=
github.com/muesli/termenv v0.16.0/go.mod h1:ZRfOIKPFDYQoDFF4Olj7/QJbW60Ol/kL1pU3VfY/Cnk=
github.com/rivo/uniseg v0.4.7 h1:WUdvkW8uEhrYfLC4ZzdpI2ztxP1I582+49Oc5Mq64VQ=
github.com/rivo/uniseg v0.4.7/go.mod h1:FN3SvrM+Zdj16jyLfmOkMNblXMcoc8DfTHruCPUcx88=
github.com/xo/terminfo v0.0.0-20220910002029-abceb7e1c41e h1:JVG44RsyaB9T2KIHavMF/ppJZNG9ZpyihvCd0w101no=
github.com/xo/terminfo v0.0.0-20220910002029-abceb7e1c41e/go.mod h1:RbqR21r5mrJuqunuUZ/Dhy/avygyECGrLceyNeo4LiM=
golang.org/x/exp v0.0.0-20231006140011-7918f672742d h1:jtJma62tbqLibJ5sFQz8bKtEM8rJBtfilJ2qTU199MI=
golang.org/x/exp v0.0.0-20231006140011-7918f672742d/go.mod h1:ldy0pHrwJyGW56pPQzzkH36rKxoZW1tw7ZJpeKx+hdo=
golang.org/x/sys v0.0.0-20210809222454-d867a43fc93e/go.mod h1:oPkhp1MJrh7nUepCBck5+mAzfO9JrbApNNgaTdGDITg=
golang.org/x/sys v0.6.0/go.mod h1:oPkhp1MJrh7nUepCBck5+mAzfO9JrbApNNgaTdGDITg=
golang.org/x/sys v0.38.0 h1:3yZWxaJjBmCWXqhN1qh02AkOnCQ1poK6oF+a7xWL6Gc=
golang.org/x/sys v0.38.0/go.mod h1:OgkHotnGiDImocRcuBABYBEXf8A9a87e/uXjp9XT3ks=
golang.org/x/text v0.3.8 h1:nAL+RVCQ9uMn3vJZbV+MRnydTJFPf8qqY42YiA6MrqY=
golang.org/x/text v0.3.8/go.mod h1:E6s5w1FMmriuDzIBO73fBruAKo1PCIq6d2Q6DHfQ8WQ=
gopkg.in/check.v1 v0.0.0-20161208181325-20d25e280405 h1:yhCVgyC4o1eVCa2tZl7eS0r+SDo693bJlVdllGtEeKM=
gopkg.in/check.v1 v0.0.0-20161208181325-20d25e280405/go.mod h1:Co6ibVJAznAaIkqp8huTwlJQCZ016jof/cbN4VW5Yz0=
gopkg.in/yaml.v3 v3.0.1 h1:fxVm/GzAzEWqLHuvctI91KS9hhNmmWOoWu0XTYJS7CA=
gopkg.in/yaml.v3 v3.0.1/go.mod h1:K4uyk7z7BCEPqu6E+C64Yfv1cQ7kz7rIZviUmN+EgEM=
```

## FILE: cmd/news/main.go

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "os"
    "path/filepath"
    "strconv"
    "strings"
    "time"

    "github.com/tik-choco/rssflow/internal/rssflow"
    "github.com/tik-choco/rssflow/internal/tui"
)

func main() {
    if err := run(os.Args[1:]); err != nil {
        fmt.Fprintln(os.Stderr, "error:", err)
        os.Exit(1)
    }
}

func run(args []string) error {
    if len(args) == 0 {
        return runTUI()
    }
    switch args[0] {
    case "init":
        return rssflow.EnsureConfig()
    case "tui", "config":
        return runTUI()
    case "paths":
        return printPaths()
    case "list":
        return listWorkflows()
    case "add-devnews", "add-developer-news":
        return addDeveloperNewsWorkflow()
    case "run":
        return runWorkflow("run", args[1:], false)
    case "test":
        return runWorkflow("test", args[1:], true)
    case "models":
        return listModels(args[1:])
    case "help", "-h", "--help":
        printHelp()
        return nil
    default:
        return fmt.Errorf("unknown command %q", args[0])
    }
}

func runTUI() error {
    if err := rssflow.EnsureConfig(); err != nil {
        return err
    }
    path, err := rssflow.ConfigPath()
    if err != nil {
        return err
    }
    return tui.Run(path)
}

func printPaths() error {
    if err := rssflow.EnsureConfig(); err != nil {
        return err
    }
    cfg, err := rssflow.ConfigPath()
    if err != nil {
        return err
    }
    state, err := rssflow.StatePath()
    if err != nil {
        return err
    }
    fmt.Println("config:", cfg)
    fmt.Println("state: ", state)
    return nil
}

func listWorkflows() error {
    cfg, _, err := loadConfig()
    if err != nil {
        return err
    }
    for _, wf := range cfg.Workflows {
        resolved := rssflow.ResolveWorkflow(cfg, wf)
        fmt.Printf("%s\tfeeds=%d\tsources=%d\tprofile=%s\tmodel=%s\n", wf.Label, len(wf.RSS.URLs), rssflow.CountConfiguredSources(wf.Sources), wf.LLM.Profile, resolved.LLM.Model)
    }
    return nil
}

func addDeveloperNewsWorkflow() error {
    cfg, path, err := loadConfig()
    if err != nil {
        return err
    }
    profile := "default"
    if len(cfg.LLMProfiles) > 0 && cfg.LLMProfiles[0].Label != "" {
        profile = cfg.LLMProfiles[0].Label
    }
    wf := rssflow.DefaultDeveloperNewsWorkflow(profile)
    replaced := false
    for i := range cfg.Workflows {
        if cfg.Workflows[i].Label == wf.Label {
            cfg.Workflows[i] = wf
            replaced = true
            break
        }
    }
    if !replaced {
        cfg.Workflows = append(cfg.Workflows, wf)
    }
    if err := rssflow.SaveConfig(path, cfg); err != nil {
        return err
    }
    if replaced {
        fmt.Println("updated workflow:", wf.Label)
    } else {
        fmt.Println("added workflow:", wf.Label)
    }
    fmt.Println("config:", path)
    return nil
}

func runWorkflow(command string, args []string, forceDryRun bool) error {
    runArgs, err := parseRunArgs(command, args)
    if err != nil {
        return err
    }
    if runArgs.Label == "" {
        return fmt.Errorf("usage: %s", workflowUsage(command))
    }
    cfg, _, err := loadConfig()
    if err != nil {
        return err
    }
    wf, ok := rssflow.FindWorkflow(cfg, runArgs.Label)
    if !ok {
        return fmt.Errorf("workflow %q not found", runArgs.Label)
    }
    statePath, err := rssflow.StatePath()
    if err != nil {
        return err
    }
    ctx, cancel := context.WithTimeout(context.Background(), runArgs.Timeout)
    defer cancel()
    result, err := rssflow.RunWorkflow(ctx, wf, statePath, rssflow.RunOptions{DryRun: runArgs.DryRun || forceDryRun, Force: runArgs.Force, Limit: runArgs.Limit})
    if err != nil {
        return err
    }
    fmt.Print(rssflow.RenderResult(result))
    return nil
}

type runArgs struct {
    Label   string
    DryRun  bool
    Force   bool
    Limit   int
    Timeout time.Duration
}

func parseRunArgs(command string, args []string) (runArgs, error) {
    out := runArgs{Timeout: 2 * time.Minute}
    for i := 0; i < len(args); i++ {
        arg := strings.TrimSpace(args[i])
        switch {
        case arg == "--dry-run":
            out.DryRun = true
        case arg == "--force-run" || arg == "--force":
            out.Force = true
        case arg == "--limit":
            i++
            if i >= len(args) {
                return out, fmt.Errorf("--limit requires a value")
            }
            n, err := strconv.Atoi(args[i])
            if err != nil {
                return out, fmt.Errorf("invalid --limit value %q", args[i])
            }
            out.Limit = n
        case strings.HasPrefix(arg, "--limit="):
            n, err := strconv.Atoi(strings.TrimPrefix(arg, "--limit="))
            if err != nil {
                return out, fmt.Errorf("invalid --limit value %q", strings.TrimPrefix(arg, "--limit="))
            }
            out.Limit = n
        case arg == "--timeout":
            i++
            if i >= len(args) {
                return out, fmt.Errorf("--timeout requires a value")
            }
            d, err := time.ParseDuration(args[i])
            if err != nil {
                return out, fmt.Errorf("invalid --timeout value %q", args[i])
            }
            out.Timeout = d
        case strings.HasPrefix(arg, "--timeout="):
            raw := strings.TrimPrefix(arg, "--timeout=")
            d, err := time.ParseDuration(raw)
            if err != nil {
                return out, fmt.Errorf("invalid --timeout value %q", raw)
            }
            out.Timeout = d
        case strings.HasPrefix(arg, "-"):
            return out, fmt.Errorf("unknown %s flag %q", command, arg)
        case out.Label == "":
            out.Label = arg
        default:
            return out, fmt.Errorf("unexpected argument %q", arg)
        }
    }
    return out, nil
}

func workflowUsage(command string) string {
    switch command {
    case "test":
        return fmt.Sprintf("%s test <label> [--force-run] [--limit N] [--timeout 2m]", commandName())
    default:
        return fmt.Sprintf("%s run <label> [--dry-run] [--force-run] [--limit N] [--timeout 2m]", commandName())
    }
}

func listModels(args []string) error {
    timeout := time.Minute
    label := ""
    for i := 0; i < len(args); i++ {
        arg := strings.TrimSpace(args[i])
        switch {
        case arg == "--timeout":
            i++
            if i >= len(args) {
                return fmt.Errorf("--timeout requires a value")
            }
            d, err := time.ParseDuration(args[i])
            if err != nil {
                return fmt.Errorf("invalid --timeout value %q", args[i])
            }
            timeout = d
        case strings.HasPrefix(arg, "--timeout="):
            raw := strings.TrimPrefix(arg, "--timeout=")
            d, err := time.ParseDuration(raw)
            if err != nil {
                return fmt.Errorf("invalid --timeout value %q", raw)
            }
            timeout = d
        case strings.HasPrefix(arg, "-"):
            return fmt.Errorf("unknown models flag %q", arg)
        case label == "":
            label = arg
        default:
            return fmt.Errorf("unexpected argument %q", arg)
        }
    }
    cfg, _, err := loadConfig()
    if err != nil {
        return err
    }
    wf := rssflow.DefaultWorkflow()
    if label != "" {
        var ok bool
        wf, ok = rssflow.FindWorkflow(cfg, label)
        if !ok {
            return fmt.Errorf("workflow %q not found", label)
        }
    } else if len(cfg.Workflows) > 0 {
        wf = rssflow.ResolveWorkflow(cfg, cfg.Workflows[0])
    }
    client, err := rssflow.NewOpenAIClient(wf.LLM)
    if err != nil {
        return err
    }
    ctx, cancel := context.WithTimeout(context.Background(), timeout)
    defer cancel()
    models, err := client.ListModels(ctx)
    if err != nil {
        return err
    }
    for _, model := range models {
        fmt.Println(model)
    }
    return nil
}

func loadConfig() (*rssflow.Config, string, error) {
    if err := rssflow.EnsureConfig(); err != nil {
        return nil, "", err
    }
    path, err := rssflow.ConfigPath()
    if err != nil {
        return nil, "", err
    }
    cfg, err := rssflow.LoadConfig(path)
    return cfg, path, err
}

func loadExistingConfig() (*rssflow.Config, error) {
    path, err := rssflow.ConfigPath()
    if err != nil {
        return nil, err
    }
    if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
        return nil, nil
    } else if err != nil {
        return nil, err
    }
    return rssflow.LoadConfig(path)
}

func commandName() string {
    name := filepath.Base(os.Args[0])
    if name == "." || name == string(filepath.Separator) || name == "" {
        return "news"
    }
    return name
}

func printHelp() {
    name := commandName()
    fmt.Printf(`%s - RSS summary workflow CLI

Usage:
  %s                  Open Bubble Tea workflow editor
  %s init             Create default config
  %s paths            Print config and state paths
  %s list             List registered workflow labels
  %s add-devnews      Add/update the developer-news agent preset
  %s run <label>      Fetch, dedupe, and summarize with OpenAI
                           Flags may be before or after the label:
                           --dry-run --force-run --limit N --timeout 2m
  %s test <label>     Fetch RSS and dedupe without OpenAI
                           Flags may be before or after the label:
                           --force-run --limit N --timeout 2m
  %s models [label]   Fetch selectable OpenAI model IDs

Scheduler command example:
  %s run daily-rss
`, name, name, name, name, name, name, name, name, name, name)
    printRegisteredRunCommands(name)
}

func printRegisteredRunCommands(name string) {
    cfg, err := loadExistingConfig()
    if err != nil || cfg == nil || len(cfg.Workflows) == 0 {
        return
    }
    printed := false
    for _, wf := range cfg.Workflows {
        if strings.TrimSpace(wf.Label) == "" {
            continue
        }
        if !printed {
            fmt.Println()
            fmt.Println("Registered run commands:")
            printed = true
        }
        fmt.Printf("  %s run %s\n", name, wf.Label)
    }
}
```

## FILE: cmd/news/main_test.go

```go
package main

import (
    "testing"
    "time"
)

func TestParseRunArgsAcceptsFlagsAfterLabel(t *testing.T) {
    got, err := parseRunArgs("run", []string{"research-nve", "--force-run", "--limit", "5", "--timeout=3m"})
    if err != nil {
        t.Fatal(err)
    }
    if got.Label != "research-nve" {
        t.Fatalf("label = %q", got.Label)
    }
    if !got.Force {
        t.Fatal("force flag was not set")
    }
    if got.Limit != 5 {
        t.Fatalf("limit = %d", got.Limit)
    }
    if got.Timeout != 3*time.Minute {
        t.Fatalf("timeout = %s", got.Timeout)
    }
}

func TestParseRunArgsAcceptsFlagsBeforeLabel(t *testing.T) {
    got, err := parseRunArgs("run", []string{"--dry-run", "--force", "--limit=2", "daily"})
    if err != nil {
        t.Fatal(err)
    }
    if got.Label != "daily" || !got.DryRun || !got.Force || got.Limit != 2 {
        t.Fatalf("unexpected args: %+v", got)
    }
}

func TestParseRunArgsAcceptsTestFlags(t *testing.T) {
    got, err := parseRunArgs("test", []string{"--force-run", "--limit=3", "--timeout", "45s", "research-nve"})
    if err != nil {
        t.Fatal(err)
    }
    if got.Label != "research-nve" || !got.Force || got.Limit != 3 || got.Timeout != 45*time.Second {
        t.Fatalf("unexpected args: %+v", got)
    }
}

func TestParseRunArgsReportsCommandInUnknownFlag(t *testing.T) {
    _, err := parseRunArgs("test", []string{"research-nve", "--bad"})
    if err == nil {
        t.Fatal("expected error")
    }
    if got, want := err.Error(), `unknown test flag "--bad"`; got != want {
        t.Fatalf("error = %q, want %q", got, want)
    }
}
```

## FILE: internal/rssflow/config.go

```go
package rssflow

import (
    "errors"
    "os"
    "path/filepath"
    "strings"

    "gopkg.in/yaml.v3"
)

const (
    AppName         = "rssflow"
    FlowsFile       = "workflows.yaml"
    StateFile       = "state.yaml"
    DirPermissions  = 0755
    FilePermissions = 0644
)

type Config struct {
    LLMProfiles []LLMProfile `yaml:"llms,omitempty"`
    Workflows   []Workflow   `yaml:"workflows"`
}

type Workflow struct {
    Label   string        `yaml:"label"`
    RSS     RSSSettings   `yaml:"rss"`
    Sources SourcesConfig `yaml:"sources,omitempty"`
    Dedupe  DedupeConfig  `yaml:"dedupe"`
    LLM     LLMConfig     `yaml:"llm"`
    Agent   AgentConfig   `yaml:"agent"`
}

type RSSSettings struct {
    URLs  []string `yaml:"urls"`
    Limit int      `yaml:"limit"`
}

type SourcesConfig struct {
    GitHub   GitHubSources   `yaml:"github,omitempty"`
    Packages PackageSources  `yaml:"packages,omitempty"`
    Security SecuritySources `yaml:"security,omitempty"`
}

type GitHubSources struct {
    TokenEnv   string                `yaml:"token_env,omitempty"`
    Releases   []string              `yaml:"releases,omitempty"`
    Tags       []string              `yaml:"tags,omitempty"`
    Advisories GitHubAdvisorySources `yaml:"advisories,omitempty"`
}

type GitHubAdvisorySources struct {
    Enabled    bool     `yaml:"enabled,omitempty"`
    Ecosystems []string `yaml:"ecosystems,omitempty"`
    Severities []string `yaml:"severities,omitempty"`
    Limit      int      `yaml:"limit,omitempty"`
}

type PackageSources struct {
    NPM    []string `yaml:"npm,omitempty"`
    PyPI   []string `yaml:"pypi,omitempty"`
    Crates []string `yaml:"crates,omitempty"`
}

type SecuritySources struct {
    NVD NVDSources `yaml:"nvd,omitempty"`
}

type NVDSources struct {
    Keywords  []string `yaml:"keywords,omitempty"`
    APIKeyEnv string   `yaml:"api_key_env,omitempty"`
    Days      int      `yaml:"days,omitempty"`
    Limit     int      `yaml:"limit,omitempty"`
}

type DedupeConfig struct {
    Enabled bool `yaml:"enabled"`
    MaxSeen int  `yaml:"max_seen"`
}

type LLMConfig struct {
    Provider    string  `yaml:"provider"`
    Profile     string  `yaml:"profile,omitempty"`
    APIKeyEnv   string  `yaml:"api_key_env"`
    Model       string  `yaml:"model"`
    BaseURL     string  `yaml:"base_url"`
    MaxTokens   int     `yaml:"max_tokens"`
    Temperature float64 `yaml:"temperature"`
}

type LLMProfile struct {
    Label       string  `yaml:"label"`
    Provider    string  `yaml:"provider"`
    APIKeyEnv   string  `yaml:"api_key_env"`
    Model       string  `yaml:"model"`
    BaseURL     string  `yaml:"base_url"`
    MaxTokens   int     `yaml:"max_tokens"`
    Temperature float64 `yaml:"temperature"`
}

type AgentConfig struct {
    Enabled        bool   `yaml:"enabled"`
    Role           string `yaml:"role"`
    Instructions   string `yaml:"instructions"`
    OutputLanguage string `yaml:"output_language"`
    OutputFormat   string `yaml:"output_format,omitempty"`
}

type State struct {
    Seen map[string][]string `yaml:"seen"`
}

const (
    OutputFormatNewsScript = "news-script"
    OutputFormatPodcast    = "podcast"
    OutputFormatArticle    = "article"
)

func OutputFormats() []string {
    return []string{OutputFormatNewsScript, OutputFormatPodcast, OutputFormatArticle}
}

func NormalizeOutputFormat(format string) string {
    switch strings.ToLower(strings.TrimSpace(format)) {
    case "", OutputFormatPodcast, "podcast-script", "podcast script", "ポッドキャスト", "ポッドキャスト台本":
        return OutputFormatPodcast
    case OutputFormatNewsScript, "news_script", "news script", "script", "broadcast", "announcer", "ニュース", "ニュース原稿", "読み原稿", "原稿":
        return OutputFormatNewsScript
    case OutputFormatArticle, "blog", "post", "written", "記事", "ブログ", "記事本文":
        return OutputFormatArticle
    default:
        return OutputFormatPodcast
    }
}

func OutputFormatLabel(format string) string {
    switch NormalizeOutputFormat(format) {
    case OutputFormatNewsScript:
        return "ニュース原稿"
    case OutputFormatArticle:
        return "記事"
    default:
        return "ポッドキャスト"
    }
}

func NextOutputFormat(format string) string {
    formats := OutputFormats()
    current := NormalizeOutputFormat(format)
    for i, candidate := range formats {
        if candidate == current {
            return formats[(i+1)%len(formats)]
        }
    }
    return OutputFormatPodcast
}

func PreviousOutputFormat(format string) string {
    formats := OutputFormats()
    current := NormalizeOutputFormat(format)
    for i, candidate := range formats {
        if candidate == current {
            return formats[(i-1+len(formats))%len(formats)]
        }
    }
    return OutputFormatPodcast
}

func DefaultWorkflow() Workflow {
    return Workflow{
        Label: "daily-rss",
        RSS: RSSSettings{
            URLs:  []string{"https://example.com/feed.xml"},
            Limit: 20,
        },
        Dedupe: DedupeConfig{Enabled: true, MaxSeen: 500},
        LLM: LLMConfig{
            Provider:    "openai",
            APIKeyEnv:   "OPENAI_API_KEY",
            Model:       "gpt-4.1-mini",
            BaseURL:     "https://api.openai.com/v1",
            MaxTokens:   900,
            Temperature: 0.2,
        },
        Agent: AgentConfig{
            Enabled:        true,
            Role:           "rss summary agent",
            Instructions:   "Prioritize important changes and write actionable bullets.",
            OutputLanguage: "Japanese",
            OutputFormat:   OutputFormatPodcast,
        },
    }
}

func DefaultDeveloperNewsWorkflow(profile string) Workflow {
    wf := Workflow{
        Label: "developer-news-agent",
        RSS: RSSSettings{
            URLs: []string{
                "https://github.blog/changelog/feed/",
                "https://blog.cloudflare.com/rss/",
                "https://webkit.org/feed/",
                "https://nodejs.org/en/feed/blog.xml",
            },
            Limit: 60,
        },
        Sources: SourcesConfig{
            GitHub: GitHubSources{
                Releases: []string{
                    "nodejs/node",
                    "golang/go",
                    "rust-lang/rust",
                    "python/cpython",
                    "kubernetes/kubernetes",
                    "vercel/next.js",
                    "facebook/react",
                    "docker/cli",
                },
                Tags: []string{
                    "tc39/proposals",
                },
                Advisories: GitHubAdvisorySources{
                    Enabled:    true,
                    Ecosystems: []string{"npm", "pip", "go", "rust", "maven"},
                    Severities: []string{"critical", "high"},
                    Limit:      30,
                },
            },
            Packages: PackageSources{
                NPM:    []string{"react", "next", "typescript", "vite"},
                PyPI:   []string{"django", "fastapi"},
                Crates: []string{"tokio", "serde"},
            },
            Security: SecuritySources{
                NVD: NVDSources{
                    Keywords: []string{"OpenSSL", "Kubernetes", "Node.js"},
                    Days:     7,
                    Limit:    20,
                },
            },
        },
        Dedupe: DedupeConfig{Enabled: true, MaxSeen: 2000},
        LLM: LLMConfig{
            Provider:    "openai",
            Profile:     profile,
            APIKeyEnv:   "OPENAI_API_KEY",
            Model:       "gpt-4.1-mini",
            BaseURL:     "https://api.openai.com/v1",
            MaxTokens:   1800,
            Temperature: 0.2,
        },
        Agent: AgentConfig{
            Enabled:        true,
            Role:           "developer news intake and verification agent",
            Instructions:   DeveloperNewsInstructions(),
            OutputLanguage: "Japanese",
            OutputFormat:   OutputFormatPodcast,
        },
    }
    return NormalizeWorkflow(wf)
}

func DeveloperNewsPrompt() string {
    return "あなたはニュース番組の編集者です。RSS/API/各種フィードの情報を、指定された形式の日本語コンテンツにしてください。公式情報や一次情報を最終根拠とし、確定情報、見通し、提案段階、当事者やコミュニティの反応を区別しながら、政治、経済、社会、国際、災害、医療、科学、文化、スポーツ、テクノロジーなど幅広い分野を扱います。"
}

func DeveloperNewsInstructions() string {
    return strings.Join([]string{
        "Output in Japanese.",
        "Group related items and remove duplicates across RSS, APIs, official announcements, public databases, and other configured sources.",
        "Write the final output in the selected output_format: news-script, podcast, or article. It must not be a summary, research note, or bullet-only briefing.",
        "Use this structure: 視聴者や読者が今知るべき理由を示すオープニング/リード, Hook/Insight/Actionで構成した厳選トピック, 中盤のコンストラクティブ・アプローチ, 明るい話題や前向きな展望で終える締め.",
        "Each item should be natural Japanese with complete sentences. Keep script and podcast topics within 300 Japanese characters.",
        "For each important item, weave Hook, Insight, and Action into the copy: what happened, why it matters, and what people, organizations, or communities should watch or do next.",
        "Prefer active voice and presenter interpretation over passive, detached wording.",
        "Start with the most important or high-impact hard news, use the middle for solutions, responses, context, or constructive perspectives, and always end with bright news or a positive outlook.",
        "Mark unconfirmed discussions, proposals, community signals, and prereleases clearly in the spoken copy.",
        "Use source URLs internally for verification, but do not include source lines, URLs, or Source labels in the final script.",
        "Do not start with phrases like '以下は要約です' or '提供されたRSSフィードの要約です'.",
        "Do not include production notes, analysis scratchpad, emoji, or instructions to the announcer unless the user explicitly asks for them.",
    }, " ")
}

func DefaultConfig() *Config {
    wf := DefaultWorkflow()
    wf.LLM = LLMConfig{Provider: "openai", Profile: "default"}
    return &Config{
        LLMProfiles: []LLMProfile{DefaultLLMProfile()},
        Workflows:   []Workflow{wf},
    }
}

func DefaultLLMProfile() LLMProfile {
    llm := DefaultWorkflow().LLM
    return LLMProfile{
        Label:       "default",
        Provider:    llm.Provider,
        APIKeyEnv:   llm.APIKeyEnv,
        Model:       llm.Model,
        BaseURL:     llm.BaseURL,
        MaxTokens:   llm.MaxTokens,
        Temperature: llm.Temperature,
    }
}

func ConfigDir() (string, error) {
    base, err := os.UserConfigDir()
    if err != nil {
        return "", err
    }
    return filepath.Join(base, AppName), nil
}

func ConfigPath() (string, error) {
    dir, err := ConfigDir()
    if err != nil {
        return "", err
    }
    return filepath.Join(dir, FlowsFile), nil
}

func StatePath() (string, error) {
    dir, err := ConfigDir()
    if err != nil {
        return "", err
    }
    return filepath.Join(dir, StateFile), nil
}

func EnsureConfig() error {
    dir, err := ConfigDir()
    if err != nil {
        return err
    }
    if err := os.MkdirAll(dir, DirPermissions); err != nil {
        return err
    }
    path, err := ConfigPath()
    if err != nil {
        return err
    }
    if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
        return SaveConfig(path, DefaultConfig())
    }
    return nil
}

func LoadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if errors.Is(err, os.ErrNotExist) {
        return DefaultConfig(), nil
    }
    if err != nil {
        return nil, err
    }
    var cfg Config
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return nil, err
    }
    if cfg.Workflows == nil {
        cfg.Workflows = []Workflow{}
    }
    if len(cfg.LLMProfiles) == 0 {
        cfg.LLMProfiles = []LLMProfile{DefaultLLMProfile()}
    }
    for i := range cfg.LLMProfiles {
        cfg.LLMProfiles[i] = NormalizeLLMProfile(cfg.LLMProfiles[i])
    }
    for i := range cfg.Workflows {
        cfg.Workflows[i] = NormalizeWorkflow(cfg.Workflows[i])
    }
    return &cfg, nil
}

func SaveConfig(path string, cfg *Config) error {
    data, err := yaml.Marshal(cfg)
    if err != nil {
        return err
    }
    return os.WriteFile(path, data, FilePermissions)
}

func LoadState(path string) (*State, error) {
    data, err := os.ReadFile(path)
    if errors.Is(err, os.ErrNotExist) {
        return &State{Seen: map[string][]string{}}, nil
    }
    if err != nil {
        return nil, err
    }
    var st State
    if err := yaml.Unmarshal(data, &st); err != nil {
        return nil, err
    }
    if st.Seen == nil {
        st.Seen = map[string][]string{}
    }
    return &st, nil
}

func SaveState(path string, st *State) error {
    data, err := yaml.Marshal(st)
    if err != nil {
        return err
    }
    return os.WriteFile(path, data, FilePermissions)
}

func FindWorkflow(cfg *Config, label string) (Workflow, bool) {
    for _, wf := range cfg.Workflows {
        if wf.Label == label {
            return ResolveWorkflow(cfg, wf), true
        }
    }
    return Workflow{}, false
}

func FindLLMProfile(cfg *Config, label string) (LLMProfile, bool) {
    for _, profile := range cfg.LLMProfiles {
        if profile.Label == label {
            return NormalizeLLMProfile(profile), true
        }
    }
    return LLMProfile{}, false
}

func ResolveWorkflow(cfg *Config, wf Workflow) Workflow {
    if cfg == nil {
        return NormalizeWorkflow(wf)
    }
    profileLabel := wf.LLM.Profile
    if profileLabel != "" {
        if profile, ok := FindLLMProfile(cfg, profileLabel); ok {
            wf.LLM = mergeLLM(profile.toConfig(), wf.LLM)
        }
    }
    return NormalizeWorkflow(wf)
}

func NormalizeLLMProfile(profile LLMProfile) LLMProfile {
    llm := NormalizeLLMConfig(profile.toConfig())
    if profile.Label == "" {
        profile.Label = "default"
    }
    profile.Provider = llm.Provider
    profile.APIKeyEnv = llm.APIKeyEnv
    profile.BaseURL = llm.BaseURL
    profile.Model = llm.Model
    profile.MaxTokens = llm.MaxTokens
    profile.Temperature = llm.Temperature
    return profile
}

func (p LLMProfile) toConfig() LLMConfig {
    return LLMConfig{
        Provider:    p.Provider,
        APIKeyEnv:   p.APIKeyEnv,
        Model:       p.Model,
        BaseURL:     p.BaseURL,
        MaxTokens:   p.MaxTokens,
        Temperature: p.Temperature,
    }
}

func mergeLLM(base, override LLMConfig) LLMConfig {
    out := base
    out.Profile = override.Profile
    if override.Provider != "" {
        out.Provider = override.Provider
    }
    if override.APIKeyEnv != "" {
        out.APIKeyEnv = override.APIKeyEnv
    }
    if override.Model != "" {
        out.Model = override.Model
    }
    if override.BaseURL != "" {
        out.BaseURL = override.BaseURL
    }
    if override.MaxTokens > 0 {
        out.MaxTokens = override.MaxTokens
    }
    if override.Temperature != 0 {
        out.Temperature = override.Temperature
    }
    return out
}

func NormalizeWorkflow(wf Workflow) Workflow {
    if wf.RSS.Limit <= 0 {
        wf.RSS.Limit = 20
    }
    if wf.Dedupe.MaxSeen <= 0 {
        wf.Dedupe.MaxSeen = 500
    }
    if wf.LLM.Profile != "" {
        if wf.LLM.Provider == "" {
            wf.LLM.Provider = "openai"
        }
    } else {
        wf.LLM = NormalizeLLMConfig(wf.LLM)
    }
    if wf.Agent.OutputLanguage == "" {
        wf.Agent.OutputLanguage = "Japanese"
    }
    wf.Agent.OutputFormat = NormalizeOutputFormat(wf.Agent.OutputFormat)
    return wf
}

func NormalizeLLMConfig(llm LLMConfig) LLMConfig {
    if llm.Provider == "" {
        llm.Provider = "openai"
    }
    if llm.APIKeyEnv == "" {
        llm.APIKeyEnv = "OPENAI_API_KEY"
    }
    if llm.BaseURL == "" {
        llm.BaseURL = "https://api.openai.com/v1"
    }
    if llm.Model == "" {
        llm.Model = "gpt-4.1-mini"
    }
    if llm.MaxTokens <= 0 {
        llm.MaxTokens = 900
    }
    return llm
}
```

## FILE: internal/rssflow/config_test.go

```go
package rssflow

import "testing"

func TestNormalizeWorkflow(t *testing.T) {
    wf := NormalizeWorkflow(Workflow{})
    if wf.RSS.Limit == 0 {
        t.Fatal("RSS limit was not defaulted")
    }
    if wf.LLM.APIKeyEnv != "OPENAI_API_KEY" {
        t.Fatalf("api key env = %q", wf.LLM.APIKeyEnv)
    }
    if wf.LLM.BaseURL == "" || wf.LLM.Model == "" {
        t.Fatalf("missing LLM defaults: %+v", wf.LLM)
    }
}

func TestResolveWorkflowUsesLLMProfile(t *testing.T) {
    cfg := &Config{
        LLMProfiles: []LLMProfile{{
            Label:       "local",
            Provider:    "openai",
            APIKeyEnv:   "LOCAL_KEY",
            BaseURL:     "http://localhost:11434/v1",
            Model:       "qwen3",
            MaxTokens:   123,
            Temperature: 0.4,
        }},
    }
    wf := NormalizeWorkflow(Workflow{
        Label: "daily",
        LLM:   LLMConfig{Profile: "local"},
    })

    resolved := ResolveWorkflow(cfg, wf)
    if resolved.LLM.BaseURL != "http://localhost:11434/v1" {
        t.Fatalf("base url = %q", resolved.LLM.BaseURL)
    }
    if resolved.LLM.Model != "qwen3" {
        t.Fatalf("model = %q", resolved.LLM.Model)
    }
    if resolved.LLM.Profile != "local" {
        t.Fatalf("profile = %q", resolved.LLM.Profile)
    }
}
```

## FILE: internal/rssflow/dedupe.go

```go
package rssflow

import (
    "crypto/sha256"
    "encoding/hex"
    "strings"
)

func FilterNewItems(items []Item, st *State, label string, cfg DedupeConfig) ([]Item, *State) {
    if st == nil {
        st = &State{Seen: map[string][]string{}}
    }
    if st.Seen == nil {
        st.Seen = map[string][]string{}
    }
    if !cfg.Enabled {
        return items, st
    }

    seen := make(map[string]bool, len(st.Seen[label]))
    for _, id := range st.Seen[label] {
        seen[id] = true
    }

    var fresh []Item
    for _, item := range items {
        key := itemKey(item)
        if seen[key] {
            continue
        }
        seen[key] = true
        fresh = append(fresh, item)
        st.Seen[label] = append([]string{key}, st.Seen[label]...)
    }

    maxSeen := cfg.MaxSeen
    if maxSeen <= 0 {
        maxSeen = 500
    }
    if len(st.Seen[label]) > maxSeen {
        st.Seen[label] = st.Seen[label][:maxSeen]
    }
    return fresh, st
}

func itemKey(item Item) string {
    raw := strings.TrimSpace(item.ID)
    if raw == "" {
        raw = strings.TrimSpace(item.Link)
    }
    if raw == "" {
        raw = strings.TrimSpace(item.Title) + "|" + strings.TrimSpace(item.Source)
    }
    sum := sha256.Sum256([]byte(raw))
    return hex.EncodeToString(sum[:])
}
```

## FILE: internal/rssflow/dedupe_test.go

```go
package rssflow

import "testing"

func TestFilterNewItems(t *testing.T) {
    items := []Item{
        {ID: "1", Title: "one"},
        {ID: "1", Title: "one duplicate"},
        {ID: "2", Title: "two"},
    }
    st := &State{Seen: map[string][]string{}}
    fresh, st := FilterNewItems(items, st, "daily", DedupeConfig{Enabled: true, MaxSeen: 10})
    if len(fresh) != 2 {
        t.Fatalf("fresh len = %d, want 2", len(fresh))
    }
    fresh, _ = FilterNewItems(items, st, "daily", DedupeConfig{Enabled: true, MaxSeen: 10})
    if len(fresh) != 0 {
        t.Fatalf("second fresh len = %d, want 0", len(fresh))
    }
}

func TestFilterNewItemsMaxSeen(t *testing.T) {
    items := []Item{{ID: "1"}, {ID: "2"}, {ID: "3"}}
    _, st := FilterNewItems(items, &State{Seen: map[string][]string{}}, "x", DedupeConfig{Enabled: true, MaxSeen: 2})
    if len(st.Seen["x"]) != 2 {
        t.Fatalf("seen len = %d, want 2", len(st.Seen["x"]))
    }
}
```

## FILE: internal/rssflow/developer_news_fallback.go

```go
package rssflow

import (
    "fmt"
    "strings"
    "unicode"
    "unicode/utf8"
)

func fallbackDeveloperNewsScript(text string) string {
    return fallbackDeveloperNewsOutput(DefaultDeveloperNewsWorkflow("default"), text)
}

func fallbackDeveloperNewsOutput(wf Workflow, text string) string {
    switch developerNewsOutputFormat(wf) {
    case OutputFormatNewsScript:
        return fallbackDeveloperNewsNewsScript(text)
    case OutputFormatArticle:
        return fallbackDeveloperNewsArticle(text)
    default:
        return fallbackDeveloperNewsPodcast(text)
    }
}

func fallbackDeveloperNewsPodcast(text string) string {
    items := extractDeveloperNewsFallbackItems(text)
    if len(items) == 0 {
        return "今日のニュースです。\n\n本日は、確認できる新しい項目はありませんでした。\n\n備えを進めつつ、新しい可能性にも目を向ける。そんな一日にしていきましょう。"
    }

    var sb strings.Builder
    sb.WriteString("今日のニュースです。影響の大きい動きから、解決策につながるヒント、最後に少し明るい話題まで、今押さえたいトピックを厳選しました。\n\n")
    for i, item := range items {
        if i >= 5 {
            break
        }
        if i > 0 {
            sb.WriteString("\n\n")
        }
        sb.WriteString(limitDeveloperNewsTopic(buildFallbackDeveloperNewsTopic(i, item), developerNewsTopicCharLimit))
        if i == 0 {
            sb.WriteString("\n\nここからは、解決策や次の動きにつながる視点です。関係する人や組織は、公式情報の更新を追いながら、早めに備えておくと安心です。")
        }
    }
    sb.WriteString("\n\n最後は、少し前向きな話題として受け止めたいところです。新しい改善や対策を取り入れながら、より安心できる次の動きにつなげていけそうです。")
    sb.WriteString("\n\n備えを進めつつ、新しい可能性にも目を向ける。そんな一日にしていきましょう。")
    return sanitizeDeveloperNewsScript(sb.String())
}

func fallbackDeveloperNewsNewsScript(text string) string {
    items := extractDeveloperNewsFallbackItems(text)
    if len(items) == 0 {
        return "今日のニュースです。\n\n本日は、確認できる新しい項目はありませんでした。\n\n以上、今日のニュースでした。"
    }

    var sb strings.Builder
    sb.WriteString("今日のニュースです。まず押さえたいのは、暮らしや社会への影響が大きい動きです。\n\n")
    for i, item := range items {
        if i >= 4 {
            break
        }
        if i > 0 {
            sb.WriteString("\n\n")
        }
        sb.WriteString(limitDeveloperNewsTopic(buildFallbackDeveloperNewsNewsTopic(i, item), developerNewsTopicCharLimit))
        if i == 0 {
            sb.WriteString("\n\nここからは、解決策や次の動きにつながる話です。関係する人や組織は、公式情報の更新を追いながら、早めに備えておくと安心です。")
        }
    }
    sb.WriteString("\n\n最後は、少し前向きな話題です。新しい改善や対策を取り入れることで、より安心できる環境につなげていけそうです。")
    sb.WriteString("\n\n以上、今日のニュースでした。")
    return sanitizeDeveloperNewsScript(sb.String())
}

func fallbackDeveloperNewsArticle(text string) string {
    items := extractDeveloperNewsFallbackItems(text)
    if len(items) == 0 {
        return "今押さえたいニュース\n\n本日は、確認できる新しい項目はありませんでした。\n\n備えを進めながら、新しい可能性にも目を向ける。その両方を考えるきっかけとして、次の更新を待ちたいところです。"
    }

    var sb strings.Builder
    sb.WriteString("今押さえたいニュース\n\n")
    sb.WriteString("影響の大きい動きから、解決策につながるヒント、最後に前向きな話題まで、今日読むべき動きを整理します。\n\n")

    sections := []string{
        "最初に見るべき影響の大きい動き",
        "解決策や次の動きにつながる選択肢",
        "前向きな展望につながる話題",
        "次に備えるための視点",
    }
    for i, item := range items {
        if i >= 4 {
            break
        }
        if i > 0 {
            sb.WriteString("\n\n")
        }
        heading := sections[i]
        if title := cleanFallbackTopicTitle(item.Title); title != "" {
            heading = title
        }
        sb.WriteString(heading)
        sb.WriteString("\n")
        sb.WriteString(buildFallbackDeveloperNewsArticleParagraph(item))
    }

    sb.WriteString("\n\n備えを進めながら、新しい可能性にも目を向ける。その両方を考えるきっかけとして見ておきたいところです。")
    return sanitizeDeveloperNewsScript(sb.String())
}

func sanitizeDeveloperNewsScript(text string) string {
    text = stripDeveloperNewsSourceLines(text)
    return strings.TrimSpace(text)
}

func stripDeveloperNewsSourceLines(text string) string {
    var lines []string
    for _, raw := range strings.Split(text, "\n") {
        if isDeveloperNewsSourceLine(raw) {
            continue
        }
        lines = append(lines, raw)
    }
    return strings.TrimSpace(strings.Join(lines, "\n"))
}

func isDeveloperNewsSourceLine(line string) bool {
    line = strings.TrimSpace(line)
    if line == "" {
        return false
    }
    lower := strings.ToLower(line)
    if strings.HasPrefix(line, "出典") ||
        strings.HasPrefix(line, "参照") ||
        strings.HasPrefix(lower, "source:") ||
        strings.HasPrefix(lower, "sources:") ||
        strings.HasPrefix(lower, "link:") ||
        strings.HasPrefix(lower, "url:") {
        return true
    }
    if strings.HasPrefix(line, "[") && strings.Contains(line, "](") {
        return true
    }
    return strings.Contains(lower, "http://") || strings.Contains(lower, "https://")
}

func developerNewsTopicsOverLimit(text string, limit int) bool {
    for _, topic := range extractDeveloperNewsScriptTopics(text) {
        if japaneseScriptCharCount(topic) > limit {
            return true
        }
    }
    return false
}

func extractDeveloperNewsScriptTopics(text string) []string {
    var topics []string
    var current []string
    flush := func() {
        if len(current) == 0 {
            return
        }
        topics = append(topics, strings.Join(current, "\n"))
        current = nil
    }
    for _, raw := range strings.Split(text, "\n") {
        line := strings.TrimSpace(raw)
        if line == "" {
            continue
        }
        if isDeveloperNewsTopicStart(line) {
            flush()
            current = []string{line}
            continue
        }
        if len(current) == 0 {
            continue
        }
        if isDeveloperNewsTopicBoundary(line) {
            flush()
            continue
        }
        current = append(current, line)
    }
    flush()
    return topics
}

func isDeveloperNewsTopicStart(line string) bool {
    naturalStarts := []string{
        "まずは、",
        "続いては、",
        "次に、",
        "もう一つ、",
    }
    for _, prefix := range naturalStarts {
        if strings.HasPrefix(line, prefix) {
            return true
        }
    }
    for i := 0; i < 10; i++ {
        if strings.HasPrefix(line, newsOrdinal(i)+"です") || strings.HasPrefix(line, newsOrdinal(i)+"は") {
            return true
        }
    }
    return false
}

func isDeveloperNewsTopicBoundary(line string) bool {
    return strings.HasPrefix(line, "ここで、対策") ||
        strings.HasPrefix(line, "ここからは、解決策") ||
        strings.HasPrefix(line, "守りの次は") ||
        strings.HasPrefix(line, "ポイントは、") ||
        strings.HasPrefix(line, "では、どう対応") ||
        strings.HasPrefix(line, "現場では、") ||
        strings.HasPrefix(line, "解決策を探る時間") ||
        strings.HasPrefix(line, "最後は明るいニュース") ||
        strings.HasPrefix(line, "最後は、少し前向き") ||
        strings.HasPrefix(line, "最後は、開発の未来") ||
        strings.HasPrefix(line, "最後は前向き") ||
        strings.HasPrefix(line, "以上、今日のデベロッパーニュース") ||
        strings.HasPrefix(line, "以上、今日のニュース") ||
        strings.HasPrefix(line, "守りを固めつつ") ||
        strings.HasPrefix(line, "備えを進めつつ") ||
        strings.HasPrefix(line, "以上、開発者向けニュース")
}

func japaneseScriptCharCount(s string) int {
    var sb strings.Builder
    for _, r := range s {
        if unicode.IsSpace(r) {
            continue
        }
        sb.WriteRune(r)
    }
    return utf8.RuneCountInString(sb.String())
}

func buildFallbackDeveloperNewsTopic(index int, item fallbackNewsItem) string {
    var sb strings.Builder
    if index == 0 {
        sb.WriteString("まずは、")
    } else {
        sb.WriteString("続いては、")
    }
    title := cleanFallbackTopicTitle(item.Title)
    sb.WriteString(title)
    if index > 0 {
        sb.WriteString("についてです")
    }
    sb.WriteString("。")
    if item.Detail != "" {
        sb.WriteString("\n")
        sb.WriteString(toSpokenSentence(item.Detail))
    }
    sb.WriteString("\nここで大事なのは、")
    sb.WriteString(fallbackInsightSentence(item))
    sb.WriteString("\n今日からは、")
    sb.WriteString(fallbackActionSentence(item))
    return sb.String()
}

func buildFallbackDeveloperNewsNewsTopic(index int, item fallbackNewsItem) string {
    var sb strings.Builder
    if index == 0 {
        sb.WriteString("まずは、")
    } else {
        sb.WriteString("続いて、")
    }
    title := cleanFallbackTopicTitle(item.Title)
    sb.WriteString(title)
    if index > 0 {
        sb.WriteString("についてです")
    }
    sb.WriteString("。")
    if item.Detail != "" {
        sb.WriteString("\n")
        sb.WriteString(toSpokenSentence(item.Detail))
    }
    sb.WriteString("\nポイントは、")
    sb.WriteString(fallbackInsightSentence(item))
    sb.WriteString("\n対応としては、")
    sb.WriteString(fallbackActionSentence(item))
    return sb.String()
}

func buildFallbackDeveloperNewsArticleParagraph(item fallbackNewsItem) string {
    var parts []string
    if item.Detail != "" {
        parts = append(parts, toSpokenSentence(item.Detail))
    }
    parts = append(parts,
        "ここで重要なのは、"+fallbackInsightSentence(item),
        "今日からは、"+fallbackActionSentence(item),
    )
    return strings.Join(parts, "")
}

func cleanFallbackTopicTitle(title string) string {
    title = strings.TrimSpace(title)
    title = strings.TrimPrefix(title, "まずは、")
    title = strings.TrimPrefix(title, "続いては、")
    title = strings.TrimPrefix(title, "次に、")
    title = strings.TrimSuffix(title, "。")
    return strings.TrimSpace(title)
}

func limitDeveloperNewsTopic(topic string, limit int) string {
    if japaneseScriptCharCount(topic) <= limit {
        return topic
    }
    lines := strings.Split(topic, "\n")
    if len(lines) > 3 {
        topic = strings.Join([]string{lines[0], lines[len(lines)-2], lines[len(lines)-1]}, "\n")
    }
    if japaneseScriptCharCount(topic) <= limit {
        return topic
    }
    return truncateJapaneseScript(topic, limit)
}

func truncateJapaneseScript(s string, limit int) string {
    if limit <= 0 {
        return ""
    }
    var out []rune
    count := 0
    for _, r := range s {
        if !unicode.IsSpace(r) {
            if count >= limit-1 {
                break
            }
            count++
        }
        out = append(out, r)
    }
    text := strings.TrimSpace(string(out))
    text = strings.TrimRight(text, "。、,. \n\t")
    if text == "" {
        return ""
    }
    return text + "。"
}

type fallbackNewsItem struct {
    Title  string
    Detail string
    Source string
}

func extractDeveloperNewsFallbackItems(text string) []fallbackNewsItem {
    lines := cleanDeveloperNewsLines(text)
    var items []fallbackNewsItem
    var current *fallbackNewsItem
    for _, raw := range strings.Split(text, "\n") {
        line := cleanDeveloperNewsLine(raw)
        if line == "" {
            continue
        }
        if isDeveloperNewsBoilerplateLine(line) {
            continue
        }
        if strings.Contains(line, "http://") || strings.Contains(line, "https://") {
            source := cleanSourceLine(line)
            if current != nil && current.Source == "" {
                current.Source = source
            }
            continue
        }
        if looksLikeFallbackTitle(line) || current == nil {
            items = append(items, fallbackNewsItem{Title: line})
            current = &items[len(items)-1]
            continue
        }
        if current.Detail == "" {
            current.Detail = line
        } else {
            current.Detail += " " + line
        }
    }
    if len(items) > 0 {
        return items
    }
    for _, line := range lines {
        items = append(items, fallbackNewsItem{Title: line})
    }
    return items
}

func cleanDeveloperNewsLines(text string) []string {
    var lines []string
    for _, raw := range strings.Split(text, "\n") {
        line := cleanDeveloperNewsLine(raw)
        if line == "" || isDeveloperNewsBoilerplateLine(line) {
            continue
        }
        lines = append(lines, line)
    }
    return lines
}

func cleanDeveloperNewsLine(line string) string {
    line = strings.TrimSpace(line)
    if line == "" {
        return ""
    }
    line = strings.TrimPrefix(line, "#")
    line = strings.TrimPrefix(line, "#")
    line = strings.TrimPrefix(line, "#")
    line = strings.TrimSpace(line)
    line = strings.TrimPrefix(line, "*")
    line = strings.TrimPrefix(line, "-")
    line = strings.TrimSpace(line)
    line = strings.ReplaceAll(line, "**", "")
    line = strings.ReplaceAll(line, "🔐", "")
    line = strings.ReplaceAll(line, "`", "")
    line = strings.TrimSpace(line)
    if strings.HasPrefix(line, "[") && strings.Contains(line, "](") {
        return cleanSourceLine(line)
    }
    return line
}

func isDeveloperNewsBoilerplateLine(line string) bool {
    line = strings.TrimSpace(line)
    return strings.HasPrefix(line, "以下は") ||
        strings.Contains(line, "要約です") ||
        strings.Contains(line, "整理しています") ||
        strings.HasPrefix(line, "開発者ニュース") ||
        strings.HasPrefix(line, "デベロッパーニュース") ||
        strings.HasPrefix(line, "今日のニュース") ||
        strings.HasPrefix(line, "本日の主な") ||
        strings.HasPrefix(line, "今日の主な") ||
        strings.HasPrefix(line, "まずは、注目すべき") ||
        strings.HasPrefix(line, "以上、開発者向けニュース")
}

func looksLikeFallbackTitle(line string) bool {
    if strings.HasSuffix(line, "です") && len([]rune(line)) <= 42 {
        return true
    }
    if strings.Contains(line, "実装課題") || strings.Contains(line, "脅威") || strings.Contains(line, "攻撃") || strings.Contains(line, "更新") {
        return len([]rune(line)) <= 60
    }
    return false
}

func newsOrdinal(index int) string {
    switch index {
    case 0:
        return "一本目"
    case 1:
        return "二本目"
    case 2:
        return "三本目"
    case 3:
        return "四本目"
    case 4:
        return "五本目"
    default:
        return fmt.Sprintf("%d本目", index+1)
    }
}

func fallbackInsightSentence(item fallbackNewsItem) string {
    text := strings.TrimSpace(item.Detail)
    if text == "" {
        text = strings.TrimSpace(item.Title)
    }
    if text == "" {
        return "関係する人や組織にとって、前提の見直しが必要になりそうな点です。"
    }
    return toSpokenSentence("関係する人や組織にとって、これまでの前提を見直すきっかけになることです。背景としては、" + text)
}

func fallbackActionSentence(item fallbackNewsItem) string {
    return "関係する情報の更新を追いながら、影響範囲や自分たちに必要な備えを確認しておくのが良さそうです。"
}

func toSpokenSentence(line string) string {
    line = strings.TrimSpace(line)
    if line == "" {
        return ""
    }
    line = strings.TrimSuffix(line, "。")
    line = strings.TrimSuffix(line, ".")
    line = strings.TrimSuffix(line, "：")
    line = strings.TrimSuffix(line, ":")
    if strings.Contains(line, "http://") || strings.Contains(line, "https://") {
        return "詳しくは、公式情報をご確認ください。"
    }
    switch {
    case strings.Contains(line, "課題:"):
        line = strings.ReplaceAll(line, "課題:", "課題として、")
    case strings.Contains(line, "対策案"):
        line = strings.ReplaceAll(line, "対策案", "対策案として")
    }
    return line + "。"
}

func cleanSourceLine(line string) string {
    line = strings.TrimSpace(line)
    if start := strings.Index(line, "http://"); start >= 0 {
        return trimURLTail(line[start:])
    }
    if start := strings.Index(line, "https://"); start >= 0 {
        return trimURLTail(line[start:])
    }
    return line
}

func trimURLTail(s string) string {
    s = strings.TrimSpace(s)
    for i, r := range s {
        if r == ')' || r == ']' || r == ' ' || r == '　' {
            return s[:i]
        }
    }
    return s
}
```

## FILE: internal/rssflow/developer_news_input.go

```go
package rssflow

import (
    "sort"
    "strings"
)

const (
    developerNewsMaxCandidateItems     = 40
    developerNewsMaxScriptInputItems   = 16
    developerNewsPromptDescriptionSize = 420
    developerNewsPromptTitleSize       = 180
)

func prepareDeveloperNewsCandidateItems(items []Item) []Item {
    items = compactDeveloperNewsItems(items)
    if len(items) <= developerNewsMaxCandidateItems {
        return items
    }
    entries := make([]developerNewsInputCandidate, 0, len(items))
    for i, item := range items {
        entries = append(entries, developerNewsInputCandidate{
            Item:     item,
            Index:    i,
            Priority: localDeveloperNewsPriority(item),
            Source:   developerNewsSourceKey(item),
            Category: developerNewsCategory(item),
        })
    }
    sort.SliceStable(entries, func(i, j int) bool {
        if entries[i].Priority == entries[j].Priority {
            return entries[i].Index < entries[j].Index
        }
        return entries[i].Priority > entries[j].Priority
    })
    return developerNewsItemsFromCandidates(selectDiverseDeveloperNewsCandidates(entries, developerNewsMaxCandidateItems))
}

func limitDeveloperNewsScriptInputItems(items []Item) []Item {
    if len(items) <= developerNewsMaxScriptInputItems {
        return items
    }
    entries := make([]developerNewsInputCandidate, 0, len(items))
    for i, item := range items {
        entries = append(entries, developerNewsInputCandidate{
            Item:     item,
            Index:    i,
            Priority: len(items) - i,
            Source:   developerNewsSourceKey(item),
            Category: developerNewsCategory(item),
        })
    }
    return developerNewsItemsFromCandidates(selectDiverseDeveloperNewsCandidates(entries, developerNewsMaxScriptInputItems))
}

func compactDeveloperNewsItems(items []Item) []Item {
    out := make([]Item, 0, len(items))
    for _, item := range items {
        item.Title = truncatePromptText(item.Title, developerNewsPromptTitleSize)
        item.Description = truncatePromptText(item.Description, developerNewsPromptDescriptionSize)
        out = append(out, item)
    }
    return out
}

type developerNewsInputCandidate struct {
    Item     Item
    Index    int
    Priority int
    Source   string
    Category string
}

func localDeveloperNewsPriority(item Item) int {
    text := strings.ToLower(item.Title + " " + item.Description + " " + item.SourceType)
    score := 0
    for _, keyword := range []string{
        "critical", "high severity", "cve-", "cvss", "vulnerability", "advisory", "security",
        "breaking news", "emergency", "disaster", "earthquake", "flood", "war", "conflict", "recall",
        "脆弱性", "セキュリティ", "緊急", "重大", "攻撃", "修正", "速報", "災害", "地震", "台風", "洪水", "戦争", "紛争", "事故", "リコール",
    } {
        if strings.Contains(text, keyword) {
            score += 30
        }
    }
    for _, keyword := range []string{
        "breaking", "deprecated", "deprecation", "eol", "end of life", "migration", "outage",
        "election", "policy", "regulation", "inflation", "rate hike", "lawsuit", "strike",
        "破壊的", "非推奨", "移行", "障害", "終了", "廃止", "選挙", "政策", "規制", "法案", "物価", "金利", "訴訟", "ストライキ",
    } {
        if strings.Contains(text, keyword) {
            score += 20
        }
    }
    for _, keyword := range []string{
        "release", "stable", "lts", "pricing", "license", "standard", "proposal",
        "support", "aid", "research", "study", "record", "award", "win",
        "リリース", "安定版", "料金", "ライセンス", "標準化", "提案", "支援", "助成", "研究", "調査", "過去最高", "受賞", "勝利",
    } {
        if strings.Contains(text, keyword) {
            score += 10
        }
    }
    switch strings.ToLower(item.SourceType) {
    case "github-advisory", "nvd":
        score += 30
    case "github-release":
        score += 10
    }
    return score
}

func selectDiverseDeveloperNewsCandidates(entries []developerNewsInputCandidate, limit int) []developerNewsInputCandidate {
    if limit <= 0 || len(entries) <= limit {
        return append([]developerNewsInputCandidate(nil), entries...)
    }
    sourceCap := diversityCap(limit, 3)
    categoryCap := diversityCap(limit, 4)
    selected := make([]developerNewsInputCandidate, 0, limit)
    used := make([]bool, len(entries))
    sourceCounts := map[string]int{}
    categoryCounts := map[string]int{}

    pick := func(enforceSource, enforceCategory bool) {
        for i, entry := range entries {
            if len(selected) >= limit {
                return
            }
            if used[i] {
                continue
            }
            if enforceSource && sourceCounts[entry.Source] >= sourceCap {
                continue
            }
            if enforceCategory && categoryCounts[entry.Category] >= categoryCap {
                continue
            }
            used[i] = true
            selected = append(selected, entry)
            sourceCounts[entry.Source]++
            categoryCounts[entry.Category]++
        }
    }

    pick(true, true)
    pick(false, true)
    pick(true, false)
    pick(false, false)
    return selected
}

func diversityCap(limit, divisor int) int {
    cap := limit / divisor
    if cap < 2 {
        return 2
    }
    return cap
}

func developerNewsItemsFromCandidates(entries []developerNewsInputCandidate) []Item {
    out := make([]Item, 0, len(entries))
    for _, entry := range entries {
        out = append(out, entry.Item)
    }
    return out
}

func developerNewsSourceKey(item Item) string {
    source := strings.TrimSpace(item.Source)
    if source != "" {
        return strings.ToLower(source)
    }
    source = strings.TrimSpace(item.SourceType)
    if source != "" {
        return strings.ToLower(source)
    }
    return "unknown"
}

func developerNewsCategory(item Item) string {
    text := strings.ToLower(item.Title + " " + item.Description + " " + item.SourceType)
    switch {
    case containsAny(text, "earthquake", "flood", "typhoon", "disaster", "accident", "recall", "災害", "地震", "台風", "洪水", "事故", "リコール"):
        return "public-safety"
    case containsAny(text, "critical", "high severity", "cve-", "cvss", "vulnerability", "advisory", "security", "脆弱性", "セキュリティ", "緊急", "重大", "攻撃", "修正"):
        return "risk"
    case containsAny(text, "election", "policy", "regulation", "law", "government", "選挙", "政策", "規制", "法案", "政府"):
        return "politics"
    case containsAny(text, "economy", "inflation", "rate", "market", "pricing", "license", "物価", "金利", "市場", "料金", "ライセンス"):
        return "economy"
    case containsAny(text, "health", "medical", "hospital", "vaccine", "医療", "健康", "病院", "ワクチン"):
        return "health"
    case containsAny(text, "breaking", "deprecated", "deprecation", "eol", "end of life", "migration", "破壊的", "非推奨", "移行", "終了", "廃止"):
        return "breaking-change"
    case containsAny(text, "outage", "incident", "障害", "停止", "インシデント"):
        return "ops"
    case containsAny(text, "release", "stable", "lts", "リリース", "安定版"):
        return "release"
    case containsAny(text, "standard", "proposal", "tc39", "ietf", "w3c", "標準化", "提案"):
        return "standards"
    case containsAny(text, "ai", "llm", "model", "生成ai", "モデル"):
        return "ai"
    case containsAny(text, "npm", "pypi", "crates", "package", "パッケージ"):
        return "package"
    case containsAny(text, "sports", "game", "match", "award", "culture", "movie", "music", "スポーツ", "試合", "受賞", "文化", "映画", "音楽"):
        return "culture-sports"
    default:
        return "general"
    }
}

func containsAny(s string, needles ...string) bool {
    for _, needle := range needles {
        if strings.Contains(s, needle) {
            return true
        }
    }
    return false
}

func truncatePromptText(s string, limit int) string {
    runes := []rune(strings.TrimSpace(s))
    if len(runes) <= limit {
        return string(runes)
    }
    if limit <= 1 {
        return string(runes[:limit])
    }
    return strings.TrimSpace(string(runes[:limit-1])) + "…"
}
```

## FILE: internal/rssflow/developer_news_rank.go

```go
package rssflow

import (
    "bytes"
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "net/http"
    "sort"
    "strings"
)

type developerNewsTopicJudgment struct {
    Index        int    `json:"index"`
    Score        int    `json:"score"`
    Tone         string `json:"tone"`
    Constructive bool   `json:"constructive"`
}

type developerNewsTopicJudgmentResponse struct {
    Topics []developerNewsTopicJudgment `json:"topics"`
}

type rankedDeveloperNewsTopic struct {
    Item         Item
    Original     int
    Score        int
    Tone         string
    Constructive bool
}

func (c *OpenAIClient) rankDeveloperNewsTopics(ctx context.Context, wf Workflow, items []Item) []Item {
    return c.rankDeveloperNewsTopicsProgress(ctx, wf, items, nil)
}

func (c *OpenAIClient) rankDeveloperNewsTopicsProgress(ctx context.Context, wf Workflow, items []Item, onProgress func(RunProgress)) []Item {
    if !isDeveloperNewsWorkflow(wf) || len(items) == 0 {
        return items
    }
    emitProgress(onProgress, "score", fmt.Sprintf("asking %s to score %d topic(s)", wf.LLM.Model, len(items)))
    judgments, err := c.judgeDeveloperNewsTopics(ctx, wf, items)
    if err != nil || len(judgments) == 0 {
        emitProgress(onProgress, "score", "topic scoring unavailable; keeping collected order")
        return items
    }
    scored := rankedDeveloperNewsTopics(items, judgments)
    emitProgress(onProgress, "score", fmt.Sprintf("received %d topic score(s)", len(judgments)), runProgressTopicsFromRanked(scored, developerNewsMaxScriptInputItems))
    sorted := sortDeveloperNewsTopicsByScore(scored)
    emitProgress(onProgress, "sort", "sorted topics by editorial score", runProgressTopicsFromRanked(sorted, developerNewsMaxScriptInputItems))
    arranged := arrangeDeveloperNewsArc(sorted)
    emitProgress(onProgress, "arc", "arranged story arc: serious lead, constructive middle, brighter close", runProgressTopicsFromRanked(arranged, developerNewsMaxScriptInputItems))
    return developerNewsItemsFromRanked(arranged)
}

func (c *OpenAIClient) judgeDeveloperNewsTopics(ctx context.Context, wf Workflow, items []Item) ([]developerNewsTopicJudgment, error) {
    if c.isOllama() {
        return c.ollamaJudgeDeveloperNewsTopics(ctx, wf, items)
    }
    reqBody := chatRequest{
        Model:       wf.LLM.Model,
        MaxTokens:   wf.LLM.MaxTokens,
        Temperature: 0,
        Messages: []chatMessage{
            {Role: "system", Content: developerNewsTopicJudgeSystemPrompt()},
            {Role: "user", Content: developerNewsTopicJudgeUserPrompt(wf, items)},
        },
    }
    c.applyCompatibilityOptions(&reqBody)
    var resp chatResponse
    if err := c.postJSON(ctx, "/chat/completions", reqBody, &resp); err != nil {
        return nil, err
    }
    if resp.Error != nil {
        return nil, errors.New(resp.Error.Message)
    }
    if len(resp.Choices) == 0 {
        return nil, errors.New("OpenAI returned no topic judgments")
    }
    return parseDeveloperNewsTopicJudgments(messageText(resp.Choices[0].Message), len(items))
}

func (c *OpenAIClient) ollamaJudgeDeveloperNewsTopics(ctx context.Context, wf Workflow, items []Item) ([]developerNewsTopicJudgment, error) {
    reqBody := ollamaChatRequest{
        Model:  wf.LLM.Model,
        Stream: false,
        Think:  false,
        Messages: []chatMessage{
            {Role: "system", Content: developerNewsTopicJudgeSystemPrompt()},
            {Role: "user", Content: developerNewsTopicJudgeUserPrompt(wf, items)},
        },
    }
    if wf.LLM.MaxTokens > 0 {
        reqBody.Options = map[string]any{"num_predict": wf.LLM.MaxTokens}
    }
    data, err := json.Marshal(reqBody)
    if err != nil {
        return nil, err
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.ollamaBaseURL()+"/api/chat", bytes.NewReader(data))
    if err != nil {
        return nil, err
    }
    req.Header.Set("Content-Type", "application/json")
    res, err := c.Client.Do(req)
    if err != nil {
        return nil, err
    }
    defer res.Body.Close()
    body, err := io.ReadAll(io.LimitReader(res.Body, 4<<20))
    if err != nil {
        return nil, err
    }
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        return nil, fmt.Errorf("Ollama HTTP %d: %s", res.StatusCode, strings.TrimSpace(string(body)))
    }
    var resp ollamaChatResponse
    if err := json.Unmarshal(body, &resp); err != nil {
        return nil, err
    }
    if resp.Error != "" {
        return nil, errors.New(resp.Error)
    }
    return parseDeveloperNewsTopicJudgments(messageText(resp.Message), len(items))
}

func developerNewsTopicJudgeSystemPrompt() string {
    return strings.Join([]string{
        "あなたはニュース番組の編集判定器です。",
        "各トピックの重要度と番組内での役割を判定し、JSONだけを返してください。",
        "scoreは0から100の整数です。公共性、影響範囲、緊急性、当事者の多さ、生活や安全への影響、制度・経済・社会の変化、信頼できる新事実を高くします。",
        "toneは hard_negative, constructive, bright, neutral のいずれかです。",
        "hard_negativeは深刻な問題や注意喚起、constructiveは解決策・対応策・改善策、brightは明るいニュースや前向きな展望です。",
        "返却形式: {\"topics\":[{\"index\":1,\"score\":90,\"tone\":\"hard_negative\",\"constructive\":false}]}",
    }, "\n")
}

func developerNewsTopicJudgeUserPrompt(wf Workflow, items []Item) string {
    var sb strings.Builder
    sb.WriteString("Workflow label: ")
    sb.WriteString(wf.Label)
    sb.WriteString("\n\nトピックごとにscoreとtoneを判定してください。重要情報を前半へ置き、番組の最後に明るいニュースを残せるようにtoneを選んでください。\n")
    for i, item := range items {
        sb.WriteString(fmt.Sprintf("\n%d. %s\n", i+1, truncatePromptText(item.Title, developerNewsPromptTitleSize)))
        if item.SourceType != "" {
            sb.WriteString("Type: " + item.SourceType + "\n")
        }
        if item.Published != "" {
            sb.WriteString("Published: " + item.Published + "\n")
        }
        if item.Description != "" {
            sb.WriteString("Description: " + truncatePromptText(item.Description, developerNewsPromptDescriptionSize) + "\n")
        }
    }
    return sb.String()
}

func parseDeveloperNewsTopicJudgments(text string, itemCount int) ([]developerNewsTopicJudgment, error) {
    text = extractJSONObject(strings.TrimSpace(text))
    var response developerNewsTopicJudgmentResponse
    if err := json.Unmarshal([]byte(text), &response); err != nil {
        var topics []developerNewsTopicJudgment
        if err := json.Unmarshal([]byte(text), &topics); err != nil {
            return nil, err
        }
        response.Topics = topics
    }
    seen := map[int]bool{}
    out := make([]developerNewsTopicJudgment, 0, len(response.Topics))
    for _, topic := range response.Topics {
        if topic.Index < 1 || topic.Index > itemCount || seen[topic.Index] {
            continue
        }
        seen[topic.Index] = true
        if topic.Score < 0 {
            topic.Score = 0
        }
        if topic.Score > 100 {
            topic.Score = 100
        }
        topic.Tone = normalizeDeveloperNewsTone(topic.Tone)
        topic.Constructive = topic.Constructive || topic.Tone == "constructive"
        out = append(out, topic)
    }
    if len(out) == 0 {
        return nil, errors.New("no valid topic judgments")
    }
    return out, nil
}

func extractJSONObject(text string) string {
    text = strings.TrimSpace(text)
    if strings.HasPrefix(text, "```") {
        text = strings.TrimPrefix(text, "```json")
        text = strings.TrimPrefix(text, "```JSON")
        text = strings.TrimPrefix(text, "```")
        text = strings.TrimSuffix(text, "```")
        text = strings.TrimSpace(text)
    }
    if strings.HasPrefix(text, "[") {
        start := strings.Index(text, "[")
        end := strings.LastIndex(text, "]")
        if start >= 0 && end > start {
            return text[start : end+1]
        }
        return text
    }
    start := strings.Index(text, "{")
    end := strings.LastIndex(text, "}")
    if start >= 0 && end > start {
        return text[start : end+1]
    }
    return text
}

func normalizeDeveloperNewsTone(tone string) string {
    tone = strings.ToLower(strings.TrimSpace(tone))
    tone = strings.ReplaceAll(tone, "-", "_")
    switch tone {
    case "hard_negative", "negative", "hard":
        return "hard_negative"
    case "constructive", "solution", "solutions":
        return "constructive"
    case "bright", "positive", "good_news":
        return "bright"
    default:
        return "neutral"
    }
}

func orderDeveloperNewsItems(items []Item, judgments []developerNewsTopicJudgment) []Item {
    return developerNewsItemsFromRanked(arrangeDeveloperNewsArc(sortDeveloperNewsTopicsByScore(rankedDeveloperNewsTopics(items, judgments))))
}

func rankedDeveloperNewsTopics(items []Item, judgments []developerNewsTopicJudgment) []rankedDeveloperNewsTopic {
    entries := make([]rankedDeveloperNewsTopic, 0, len(items))
    byIndex := map[int]developerNewsTopicJudgment{}
    for _, judgment := range judgments {
        byIndex[judgment.Index] = judgment
    }
    for i, item := range items {
        judgment, ok := byIndex[i+1]
        score := 50
        tone := "neutral"
        constructive := false
        if ok {
            score = judgment.Score
            tone = judgment.Tone
            constructive = judgment.Constructive
        }
        entries = append(entries, rankedDeveloperNewsTopic{
            Item:         item,
            Original:     i,
            Score:        score,
            Tone:         tone,
            Constructive: constructive,
        })
    }
    return entries
}

func sortDeveloperNewsTopicsByScore(entries []rankedDeveloperNewsTopic) []rankedDeveloperNewsTopic {
    out := append([]rankedDeveloperNewsTopic(nil), entries...)
    sort.SliceStable(out, func(i, j int) bool {
        if out[i].Score == out[j].Score {
            return out[i].Original < out[j].Original
        }
        return out[i].Score > out[j].Score
    })
    return out
}

func developerNewsItemsFromRanked(entries []rankedDeveloperNewsTopic) []Item {
    out := make([]Item, 0, len(entries))
    for _, entry := range entries {
        out = append(out, entry.Item)
    }
    return out
}

func runProgressTopicsFromRanked(entries []rankedDeveloperNewsTopic, limit int) []RunProgressTopic {
    if limit <= 0 || limit > len(entries) {
        limit = len(entries)
    }
    out := make([]RunProgressTopic, 0, limit)
    for i := 0; i < limit; i++ {
        entry := entries[i]
        out = append(out, RunProgressTopic{
            Rank:  i + 1,
            Title: entry.Item.Title,
            Score: entry.Score,
            Tone:  entry.Tone,
        })
    }
    return out
}

func runProgressTopicsFromItems(items []Item, score int, tone string) []RunProgressTopic {
    out := make([]RunProgressTopic, 0, len(items))
    for i, item := range items {
        out = append(out, RunProgressTopic{
            Rank:  i + 1,
            Title: item.Title,
            Score: score,
            Tone:  tone,
        })
    }
    return out
}

func arrangeDeveloperNewsArc(entries []rankedDeveloperNewsTopic) []rankedDeveloperNewsTopic {
    if len(entries) < 3 {
        return entries
    }
    work := append([]rankedDeveloperNewsTopic(nil), entries...)
    firstIndex := bestTopicIndex(work, func(entry rankedDeveloperNewsTopic) bool {
        return entry.Tone == "hard_negative"
    })
    if firstIndex < 0 {
        firstIndex = 0
    }
    first := work[firstIndex]
    work = removeRankedDeveloperNewsTopic(work, firstIndex)

    lastIndex := bestTopicIndex(work, func(entry rankedDeveloperNewsTopic) bool {
        return entry.Tone == "bright"
    })
    if lastIndex < 0 {
        lastIndex = bestTopicIndex(work, func(entry rankedDeveloperNewsTopic) bool {
            return entry.Tone == "constructive" || entry.Constructive
        })
    }
    var last *rankedDeveloperNewsTopic
    if lastIndex >= 0 {
        entry := work[lastIndex]
        last = &entry
        work = removeRankedDeveloperNewsTopic(work, lastIndex)
    }

    constructiveIndex := bestTopicIndex(work, func(entry rankedDeveloperNewsTopic) bool {
        return entry.Tone == "constructive" || entry.Constructive
    })
    var constructive *rankedDeveloperNewsTopic
    if constructiveIndex >= 0 {
        entry := work[constructiveIndex]
        constructive = &entry
        work = removeRankedDeveloperNewsTopic(work, constructiveIndex)
    }

    ordered := []rankedDeveloperNewsTopic{first}
    if constructive != nil {
        midpoint := len(work) / 2
        ordered = append(ordered, work[:midpoint]...)
        ordered = append(ordered, *constructive)
        ordered = append(ordered, work[midpoint:]...)
    } else {
        ordered = append(ordered, work...)
    }
    if last != nil {
        ordered = append(ordered, *last)
    }
    return ordered
}

func bestTopicIndex(entries []rankedDeveloperNewsTopic, match func(rankedDeveloperNewsTopic) bool) int {
    best := -1
    for i, entry := range entries {
        if !match(entry) {
            continue
        }
        if best < 0 || entry.Score > entries[best].Score || (entry.Score == entries[best].Score && entry.Original < entries[best].Original) {
            best = i
        }
    }
    return best
}

func removeRankedDeveloperNewsTopic(entries []rankedDeveloperNewsTopic, index int) []rankedDeveloperNewsTopic {
    return append(entries[:index], entries[index+1:]...)
}
```

## FILE: internal/rssflow/developer_news_script.go

```go
[Binary file]
```

## FILE: internal/rssflow/openai.go

```go
package rssflow

import (
    "bufio"
    "bytes"
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "net/http"
    "os"
    "sort"
    "strings"
    "time"
)

type OpenAIClient struct {
    APIKey  string
    BaseURL string
    Client  *http.Client
}

type chatRequest struct {
    Model           string        `json:"model"`
    Messages        []chatMessage `json:"messages"`
    MaxTokens       int           `json:"max_tokens,omitempty"`
    Temperature     float64       `json:"temperature,omitempty"`
    Stream          bool          `json:"stream,omitempty"`
    ReasoningEffort string        `json:"reasoning_effort,omitempty"`
    Reasoning       *reasoning    `json:"reasoning,omitempty"`
    Think           any           `json:"think,omitempty"`
}

type reasoning struct {
    Effort string `json:"effort,omitempty"`
}

type chatMessage struct {
    Role             string `json:"role"`
    Content          string `json:"content"`
    ReasoningContent string `json:"reasoning_content,omitempty"`
    Thinking         string `json:"thinking,omitempty"`
}

type chatResponse struct {
    Choices []struct {
        Message chatMessage `json:"message"`
    } `json:"choices"`
    Error *apiError `json:"error,omitempty"`
}

type chatStreamResponse struct {
    Type    string `json:"type,omitempty"`
    Delta   string `json:"delta,omitempty"`
    Text    string `json:"text,omitempty"`
    Content string `json:"content,omitempty"`
    Choices []struct {
        Delta struct {
            Content          string `json:"content"`
            Reasoning        string `json:"reasoning"`
            ReasoningContent string `json:"reasoning_content"`
            Text             string `json:"text"`
            Thinking         string `json:"thinking"`
        } `json:"delta"`
        Message  chatMessage `json:"message"`
        Text     string      `json:"text"`
        Thinking string      `json:"thinking"`
    } `json:"choices"`
    Message *struct {
        Content  string `json:"content"`
        Thinking string `json:"thinking"`
    } `json:"message,omitempty"`
    Response  string `json:"response,omitempty"`
    Thinking  string `json:"thinking,omitempty"`
    Reasoning string `json:"reasoning,omitempty"`
    Output    []struct {
        Content []struct {
            Text string `json:"text"`
            Type string `json:"type"`
        } `json:"content"`
    } `json:"output,omitempty"`
    Error *apiError `json:"error,omitempty"`
}

type modelsResponse struct {
    Data []struct {
        ID string `json:"id"`
    } `json:"data"`
    Error *apiError `json:"error,omitempty"`
}

type ollamaChatRequest struct {
    Model    string         `json:"model"`
    Messages []chatMessage  `json:"messages"`
    Stream   bool           `json:"stream"`
    Think    bool           `json:"think,omitempty"`
    Options  map[string]any `json:"options,omitempty"`
}

type ollamaChatResponse struct {
    Message chatMessage `json:"message"`
    Done    bool        `json:"done"`
    Error   string      `json:"error,omitempty"`
}

type apiError struct {
    Message string `json:"message"`
}

func NewOpenAIClient(llm LLMConfig) (*OpenAIClient, error) {
    apiKey := strings.TrimSpace(os.Getenv(llm.APIKeyEnv))
    baseURL := strings.TrimRight(llm.BaseURL, "/")
    if baseURL == "" {
        baseURL = "https://api.openai.com/v1"
    }
    return &OpenAIClient{APIKey: apiKey, BaseURL: baseURL, Client: &http.Client{Timeout: 90 * time.Second}}, nil
}

func (c *OpenAIClient) Summarize(ctx context.Context, wf Workflow, items []Item) (string, error) {
    return c.SummarizeProgress(ctx, wf, items, nil)
}

func (c *OpenAIClient) SummarizeProgress(ctx context.Context, wf Workflow, items []Item, onProgress func(RunProgress)) (string, error) {
    if len(items) == 0 {
        return "No new items.", nil
    }
    if isDeveloperNewsWorkflow(wf) {
        originalCount := len(items)
        items = prepareDeveloperNewsCandidateItems(items)
        emitProgress(onProgress, "candidate", fmt.Sprintf("selected %d candidate topic(s) from %d new item(s)", len(items), originalCount))
        items = c.rankDeveloperNewsTopicsProgress(ctx, wf, items, onProgress)
        items = limitDeveloperNewsScriptInputItems(items)
        emitProgress(onProgress, "limit", fmt.Sprintf("limited final script input to %d topic(s)", len(items)))
        emitProgress(onProgress, "limit", "final topic order", runProgressTopicsFromItems(items, 0, ""))
    }
    if c.isOllama() {
        return c.ollamaSummarize(ctx, wf, items)
    }
    emitProgress(onProgress, "generate", fmt.Sprintf("streaming output from %s", wf.LLM.Model))
    reqBody := chatRequest{
        Model:       wf.LLM.Model,
        MaxTokens:   wf.LLM.MaxTokens,
        Temperature: wf.LLM.Temperature,
        Messages: []chatMessage{
            {Role: "system", Content: buildSystemPrompt(wf)},
            {Role: "user", Content: buildUserPrompt(wf, items)},
        },
    }
    c.applyCompatibilityOptions(&reqBody)
    var resp chatResponse
    if err := c.postJSON(ctx, "/chat/completions", reqBody, &resp); err != nil {
        return "", err
    }
    if resp.Error != nil {
        return "", errors.New(resp.Error.Message)
    }
    if len(resp.Choices) == 0 {
        return "", errors.New("OpenAI returned no choices")
    }
    content := strings.TrimSpace(messageText(resp.Choices[0].Message))
    if content == "" {
        return "", errors.New("OpenAI returned empty content")
    }
    return c.finalizeDeveloperNewsScript(ctx, wf, content)
}

func (c *OpenAIClient) Ping(ctx context.Context, llm LLMConfig) (string, error) {
    wf := Workflow{
        Label: "llm-ping",
        LLM:   NormalizeLLMConfig(llm),
    }
    items := []Item{{
        Title:       "LLM connection test",
        Description: "Reply with exactly: pong",
    }}
    return c.Summarize(ctx, wf, items)
}

func (c *OpenAIClient) StreamPing(ctx context.Context, llm LLMConfig, onDelta func(string)) (string, error) {
    wf := Workflow{
        Label: "llm-stream-ping",
        LLM:   NormalizeLLMConfig(llm),
    }
    items := []Item{{
        Title:       "LLM streaming connection test",
        Description: "Reply with exactly this sentence: streaming pong.",
    }}
    return c.StreamSummarize(ctx, wf, items, onDelta)
}

func (c *OpenAIClient) StreamSummarize(ctx context.Context, wf Workflow, items []Item, onDelta func(string)) (string, error) {
    return c.StreamSummarizeProgress(ctx, wf, items, nil, onDelta)
}

func (c *OpenAIClient) StreamSummarizeProgress(ctx context.Context, wf Workflow, items []Item, onProgress func(RunProgress), onDelta func(string)) (string, error) {
    if len(items) == 0 {
        return "No new items.", nil
    }
    if isDeveloperNewsWorkflow(wf) {
        text, err := c.SummarizeProgress(ctx, wf, items, onProgress)
        if err != nil {
            return "", err
        }
        if onDelta != nil && text != "" {
            onDelta(text)
        }
        return text, nil
    }
    if c.isOllama() {
        emitProgress(onProgress, "generate", fmt.Sprintf("streaming output from %s", wf.LLM.Model))
        return c.ollamaStreamSummarize(ctx, wf, items, onDelta)
    }
    emitProgress(onProgress, "generate", fmt.Sprintf("streaming output from %s", wf.LLM.Model))
    reqBody := chatRequest{
        Model:       wf.LLM.Model,
        MaxTokens:   wf.LLM.MaxTokens,
        Temperature: wf.LLM.Temperature,
        Stream:      true,
        Messages: []chatMessage{
            {Role: "system", Content: buildSystemPrompt(wf)},
            {Role: "user", Content: buildUserPrompt(wf, items)},
        },
    }
    c.applyCompatibilityOptions(&reqBody)
    data, err := json.Marshal(reqBody)
    if err != nil {
        return "", err
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/chat/completions", bytes.NewReader(data))
    if err != nil {
        return "", err
    }
    c.setAuthHeader(req)
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Accept", "text/event-stream")
    res, err := c.Client.Do(req)
    if err != nil {
        return "", err
    }
    defer res.Body.Close()
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        body, _ := io.ReadAll(io.LimitReader(res.Body, 4<<20))
        var out chatResponse
        if err := json.Unmarshal(body, &out); err == nil && out.Error != nil {
            return "", errors.New(out.Error.Message)
        }
        return "", fmt.Errorf("OpenAI HTTP %d", res.StatusCode)
    }
    if !strings.Contains(strings.ToLower(res.Header.Get("Content-Type")), "text/event-stream") {
        body, err := io.ReadAll(io.LimitReader(res.Body, 4<<20))
        if err != nil {
            return "", err
        }
        text, err := parseChatContent(body)
        if err != nil {
            return "", err
        }
        if onDelta != nil && text != "" {
            onDelta(text)
        }
        return strings.TrimSpace(text), nil
    }

    var sb strings.Builder
    scanner := bufio.NewScanner(res.Body)
    scanner.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
    for scanner.Scan() {
        line := strings.TrimSpace(scanner.Text())
        if line == "" || strings.HasPrefix(line, ":") {
            continue
        }
        if !strings.HasPrefix(line, "data:") {
            if strings.HasPrefix(line, "{") {
                text, err := parseChatContent([]byte(line))
                if err != nil {
                    return "", err
                }
                if text != "" {
                    sb.WriteString(text)
                    if onDelta != nil {
                        onDelta(text)
                    }
                }
            }
            continue
        }
        payload := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
        if payload == "[DONE]" {
            break
        }
        var chunk chatStreamResponse
        if err := json.Unmarshal([]byte(payload), &chunk); err != nil {
            return "", err
        }
        if chunk.Error != nil {
            return "", errors.New(chunk.Error.Message)
        }
        if chunk.Type == "response.output_text.delta" && chunk.Delta != "" {
            sb.WriteString(chunk.Delta)
            if onDelta != nil {
                onDelta(chunk.Delta)
            }
            continue
        }
        if chunk.Text != "" {
            sb.WriteString(chunk.Text)
            if onDelta != nil {
                onDelta(chunk.Text)
            }
            continue
        }
        if chunk.Content != "" {
            sb.WriteString(chunk.Content)
            if onDelta != nil {
                onDelta(chunk.Content)
            }
            continue
        }
        if chunk.Thinking != "" {
            sb.WriteString(chunk.Thinking)
            if onDelta != nil {
                onDelta(chunk.Thinking)
            }
            continue
        }
        for _, choice := range chunk.Choices {
            delta := choice.Delta.Content
            if delta == "" {
                delta = choice.Delta.Reasoning
            }
            if delta == "" {
                delta = choice.Delta.ReasoningContent
            }
            if delta == "" {
                delta = choice.Delta.Thinking
            }
            if delta == "" {
                delta = choice.Delta.Text
            }
            if delta == "" {
                delta = choice.Text
            }
            if delta == "" {
                delta = choice.Thinking
            }
            if delta == "" {
                delta = messageText(choice.Message)
            }
            if delta == "" {
                continue
            }
            sb.WriteString(delta)
            if onDelta != nil {
                onDelta(delta)
            }
        }
    }
    if err := scanner.Err(); err != nil {
        return "", err
    }
    text := strings.TrimSpace(sb.String())
    if text == "" {
        text, err = c.Summarize(ctx, wf, items)
        if err != nil {
            return "", err
        }
        if onDelta != nil && text != "" {
            onDelta(text)
        }
        text = strings.TrimSpace(text)
        if text == "" {
            return "", errors.New("OpenAI returned empty content")
        }
        return text, nil
    }
    if shouldRewriteDeveloperNews(text, wf) {
        rewritten, err := c.finalizeDeveloperNewsScript(ctx, wf, text)
        if err != nil {
            return "", err
        }
        return rewritten, nil
    }
    return text, nil
}

func parseChatContent(data []byte) (string, error) {
    var resp chatResponse
    if err := json.Unmarshal(data, &resp); err == nil {
        if resp.Error != nil {
            return "", errors.New(resp.Error.Message)
        }
        if len(resp.Choices) > 0 {
            return messageText(resp.Choices[0].Message), nil
        }
    }
    var streamResp chatStreamResponse
    if err := json.Unmarshal(data, &streamResp); err != nil {
        return "", err
    }
    if streamResp.Error != nil {
        return "", errors.New(streamResp.Error.Message)
    }
    if streamResp.Message != nil && streamResp.Message.Content != "" {
        return streamResp.Message.Content, nil
    }
    if streamResp.Message != nil && streamResp.Message.Thinking != "" {
        return streamResp.Message.Thinking, nil
    }
    if streamResp.Response != "" {
        return streamResp.Response, nil
    }
    if streamResp.Thinking != "" {
        return streamResp.Thinking, nil
    }
    if streamResp.Reasoning != "" {
        return streamResp.Reasoning, nil
    }
    if streamResp.Text != "" {
        return streamResp.Text, nil
    }
    if streamResp.Content != "" {
        return streamResp.Content, nil
    }
    if streamResp.Type == "response.output_text.delta" && streamResp.Delta != "" {
        return streamResp.Delta, nil
    }
    for _, output := range streamResp.Output {
        for _, content := range output.Content {
            if content.Text != "" {
                return content.Text, nil
            }
        }
    }
    var sb strings.Builder
    for _, choice := range streamResp.Choices {
        switch {
        case choice.Delta.Content != "":
            sb.WriteString(choice.Delta.Content)
        case choice.Delta.Reasoning != "":
            sb.WriteString(choice.Delta.Reasoning)
        case choice.Delta.ReasoningContent != "":
            sb.WriteString(choice.Delta.ReasoningContent)
        case choice.Delta.Thinking != "":
            sb.WriteString(choice.Delta.Thinking)
        case choice.Delta.Text != "":
            sb.WriteString(choice.Delta.Text)
        case choice.Text != "":
            sb.WriteString(choice.Text)
        case choice.Thinking != "":
            sb.WriteString(choice.Thinking)
        case messageText(choice.Message) != "":
            sb.WriteString(messageText(choice.Message))
        }
    }
    return sb.String(), nil
}

func messageText(message chatMessage) string {
    if message.Content != "" {
        return message.Content
    }
    if message.Thinking != "" {
        return message.Thinking
    }
    return message.ReasoningContent
}

func (c *OpenAIClient) applyCompatibilityOptions(req *chatRequest) {
    baseURL := strings.ToLower(c.BaseURL)
    model := strings.ToLower(req.Model)
    if strings.Contains(baseURL, "localhost:11434") || strings.Contains(baseURL, "127.0.0.1:11434") || strings.Contains(model, ":") {
        req.ReasoningEffort = "none"
        req.Reasoning = &reasoning{Effort: "none"}
        req.Think = false
    }
}

func (c *OpenAIClient) isOllama() bool {
    baseURL := strings.ToLower(c.BaseURL)
    return strings.Contains(baseURL, "localhost:11434") || strings.Contains(baseURL, "127.0.0.1:11434")
}

func (c *OpenAIClient) ollamaBaseURL() string {
    baseURL := strings.TrimRight(c.BaseURL, "/")
    return strings.TrimSuffix(baseURL, "/v1")
}

func (c *OpenAIClient) ollamaRequest(wf Workflow, items []Item, stream bool) ollamaChatRequest {
    options := map[string]any{}
    if wf.LLM.MaxTokens > 0 {
        options["num_predict"] = wf.LLM.MaxTokens
    }
    if wf.LLM.Temperature != 0 {
        options["temperature"] = wf.LLM.Temperature
    }
    return ollamaChatRequest{
        Model:   wf.LLM.Model,
        Stream:  stream,
        Think:   false,
        Options: options,
        Messages: []chatMessage{
            {Role: "system", Content: buildSystemPrompt(wf)},
            {Role: "user", Content: buildUserPrompt(wf, items)},
        },
    }
}

func (c *OpenAIClient) ollamaSummarize(ctx context.Context, wf Workflow, items []Item) (string, error) {
    reqBody := c.ollamaRequest(wf, items, false)
    data, err := json.Marshal(reqBody)
    if err != nil {
        return "", err
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.ollamaBaseURL()+"/api/chat", bytes.NewReader(data))
    if err != nil {
        return "", err
    }
    req.Header.Set("Content-Type", "application/json")
    res, err := c.Client.Do(req)
    if err != nil {
        return "", err
    }
    defer res.Body.Close()
    body, err := io.ReadAll(io.LimitReader(res.Body, 4<<20))
    if err != nil {
        return "", err
    }
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        return "", fmt.Errorf("Ollama HTTP %d: %s", res.StatusCode, strings.TrimSpace(string(body)))
    }
    var resp ollamaChatResponse
    if err := json.Unmarshal(body, &resp); err != nil {
        return "", err
    }
    if resp.Error != "" {
        return "", errors.New(resp.Error)
    }
    content := strings.TrimSpace(messageText(resp.Message))
    if content == "" {
        return "", errors.New("Ollama returned empty content")
    }
    return c.finalizeDeveloperNewsScript(ctx, wf, content)
}

func (c *OpenAIClient) ollamaStreamSummarize(ctx context.Context, wf Workflow, items []Item, onDelta func(string)) (string, error) {
    reqBody := c.ollamaRequest(wf, items, true)
    data, err := json.Marshal(reqBody)
    if err != nil {
        return "", err
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.ollamaBaseURL()+"/api/chat", bytes.NewReader(data))
    if err != nil {
        return "", err
    }
    req.Header.Set("Content-Type", "application/json")
    res, err := c.Client.Do(req)
    if err != nil {
        return "", err
    }
    defer res.Body.Close()
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        body, _ := io.ReadAll(io.LimitReader(res.Body, 4<<20))
        return "", fmt.Errorf("Ollama HTTP %d: %s", res.StatusCode, strings.TrimSpace(string(body)))
    }
    decoder := json.NewDecoder(res.Body)
    var sb strings.Builder
    for {
        var chunk ollamaChatResponse
        if err := decoder.Decode(&chunk); err != nil {
            if errors.Is(err, io.EOF) {
                break
            }
            return "", err
        }
        if chunk.Error != "" {
            return "", errors.New(chunk.Error)
        }
        delta := messageText(chunk.Message)
        if delta != "" {
            sb.WriteString(delta)
            if onDelta != nil {
                onDelta(delta)
            }
        }
        if chunk.Done {
            break
        }
    }
    text := strings.TrimSpace(sb.String())
    if text == "" {
        return c.ollamaSummarize(ctx, wf, items)
    }
    if shouldRewriteDeveloperNews(text, wf) {
        rewritten, err := c.finalizeDeveloperNewsScript(ctx, wf, text)
        if err != nil {
            return "", err
        }
        return rewritten, nil
    }
    return text, nil
}

func (c *OpenAIClient) ListModels(ctx context.Context) ([]string, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+"/models", nil)
    if err != nil {
        return nil, err
    }
    c.setAuthHeader(req)
    res, err := c.Client.Do(req)
    if err != nil {
        return nil, err
    }
    defer res.Body.Close()
    body, err := io.ReadAll(io.LimitReader(res.Body, 2<<20))
    if err != nil {
        return nil, err
    }
    var out modelsResponse
    if err := json.Unmarshal(body, &out); err != nil {
        return nil, err
    }
    if out.Error != nil {
        return nil, errors.New(out.Error.Message)
    }
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        return nil, fmt.Errorf("OpenAI HTTP %d", res.StatusCode)
    }
    models := make([]string, 0, len(out.Data))
    for _, model := range out.Data {
        if model.ID != "" {
            models = append(models, model.ID)
        }
    }
    sort.Strings(models)
    return models, nil
}

func (c *OpenAIClient) postJSON(ctx context.Context, path string, reqBody any, out any) error {
    data, err := json.Marshal(reqBody)
    if err != nil {
        return err
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+path, bytes.NewReader(data))
    if err != nil {
        return err
    }
    c.setAuthHeader(req)
    req.Header.Set("Content-Type", "application/json")
    res, err := c.Client.Do(req)
    if err != nil {
        return err
    }
    defer res.Body.Close()
    body, err := io.ReadAll(io.LimitReader(res.Body, 4<<20))
    if err != nil {
        return err
    }
    if err := json.Unmarshal(body, out); err != nil {
        return err
    }
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        return fmt.Errorf("OpenAI HTTP %d", res.StatusCode)
    }
    return nil
}

func (c *OpenAIClient) setAuthHeader(req *http.Request) {
    if c.APIKey != "" {
        req.Header.Set("Authorization", "Bearer "+c.APIKey)
    }
}
```

## FILE: internal/rssflow/openai_prompts.go

```go
package rssflow

import (
    "fmt"
    "strings"
)

func buildSystemPrompt(wf Workflow) string {
    parts := []string{baseSystemPrompt(wf)}
    if wf.Agent.Enabled && !isDeveloperNewsWorkflow(wf) {
        if wf.Agent.Role != "" {
            parts = append(parts, "Agent role: "+wf.Agent.Role)
        }
        if wf.Agent.Instructions != "" {
            parts = append(parts, "Agent instructions: "+wf.Agent.Instructions)
        }
        if wf.Agent.OutputLanguage != "" {
            parts = append(parts, "Output language: "+wf.Agent.OutputLanguage)
        }
    }
    if isDeveloperNewsWorkflow(wf) {
        parts = append(parts, developerNewsOutputContract(wf))
    }
    return strings.Join(parts, "\n")
}

func baseSystemPrompt(wf Workflow) string {
    if isDeveloperNewsWorkflow(wf) {
        return DeveloperNewsPrompt()
    }
    return "Summarize the input items. Group duplicates, keep it concise, prioritize important changes, and include source links."
}

func buildUserPrompt(wf Workflow, items []Item) string {
    var sb strings.Builder
    sb.WriteString("Workflow label: ")
    sb.WriteString(wf.Label)
    if isDeveloperNewsWorkflow(wf) {
        sb.WriteString("\n\n最終成果物は")
        sb.WriteString(developerNewsOutputFormatName(wf))
        sb.WriteString("です。要約、箇条書きダイジェスト、調査メモは出力しないでください。入力順は編集判定器のスコアを反映しています。")
    }
    sb.WriteString("\n\nInput items:\n")
    for i, item := range items {
        sb.WriteString(fmt.Sprintf("\n%d. %s\n", i+1, promptItemTitle(wf, item)))
        if item.SourceType != "" {
            sb.WriteString("Type: " + item.SourceType + "\n")
        }
        if item.Source != "" {
            sb.WriteString("Source: " + item.Source + "\n")
        }
        if item.Published != "" {
            sb.WriteString("Published: " + item.Published + "\n")
        }
        if item.Link != "" {
            sb.WriteString("Link: " + item.Link + "\n")
        }
        if item.Description != "" {
            sb.WriteString("Description: " + promptItemDescription(wf, item) + "\n")
        }
    }
    if isDeveloperNewsWorkflow(wf) {
        sb.WriteString("\nこの入力のURLやSourceは事実確認用です。最終出力には出典行、URL、Source表記を入れないでください。\n")
        sb.WriteString("\n\n")
        sb.WriteString(developerNewsFinalUserInstruction(wf))
    }
    return sb.String()
}

func promptItemTitle(wf Workflow, item Item) string {
    if isDeveloperNewsWorkflow(wf) {
        return truncatePromptText(item.Title, developerNewsPromptTitleSize)
    }
    return item.Title
}

func promptItemDescription(wf Workflow, item Item) string {
    if isDeveloperNewsWorkflow(wf) {
        return truncatePromptText(item.Description, developerNewsPromptDescriptionSize)
    }
    return item.Description
}

func isDeveloperNewsWorkflow(wf Workflow) bool {
    label := strings.ToLower(strings.TrimSpace(wf.Label))
    role := strings.ToLower(strings.TrimSpace(wf.Agent.Role))
    if strings.HasPrefix(label, "llm-") {
        return false
    }
    if wf.Agent.Enabled {
        return true
    }
    return strings.Contains(label, "developer-news") ||
        strings.Contains(label, "news") ||
        strings.Contains(label, "rss") ||
        strings.Contains(role, "developer news") ||
        strings.Contains(role, "announcer")
}
```

## FILE: internal/rssflow/openai_test.go

```go
package rssflow

import (
    "context"
    "io"
    "net/http"
    "net/http/httptest"
    "strconv"
    "strings"
    "testing"
)

func TestListModelsAllowsMissingAPIKey(t *testing.T) {
    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if got := r.Header.Get("Authorization"); got != "" {
            t.Fatalf("Authorization header = %q", got)
        }
        w.Header().Set("Content-Type", "application/json")
        _, _ = w.Write([]byte(`{"data":[{"id":"gpt-local"}]}`))
    }))
    defer server.Close()

    client, err := NewOpenAIClient(LLMConfig{
        APIKeyEnv: "RSSFLOW_TEST_MISSING_API_KEY",
        BaseURL:   server.URL,
    })
    if err != nil {
        t.Fatal(err)
    }

    models, err := client.ListModels(context.Background())
    if err != nil {
        t.Fatal(err)
    }
    if len(models) != 1 || models[0] != "gpt-local" {
        t.Fatalf("models = %#v", models)
    }
}

func TestNormalizeOutputFormat(t *testing.T) {
    cases := map[string]string{
        "":              OutputFormatPodcast,
        "podcast":       OutputFormatPodcast,
        "ポッドキャスト":       OutputFormatPodcast,
        "news_script":   OutputFormatNewsScript,
        "ニュース原稿":        OutputFormatNewsScript,
        "読み原稿":          OutputFormatNewsScript,
        "article":       OutputFormatArticle,
        "記事":            OutputFormatArticle,
        "unknown-value": OutputFormatPodcast,
    }
    for input, want := range cases {
        if got := NormalizeOutputFormat(input); got != want {
            t.Fatalf("NormalizeOutputFormat(%q) = %q, want %q", input, got, want)
        }
    }
    if got := NextOutputFormat(OutputFormatNewsScript); got != OutputFormatPodcast {
        t.Fatalf("NextOutputFormat(news-script) = %q, want podcast", got)
    }
    if got := NextOutputFormat(OutputFormatPodcast); got != OutputFormatArticle {
        t.Fatalf("NextOutputFormat(podcast) = %q, want article", got)
    }
    if got := NextOutputFormat(OutputFormatArticle); got != OutputFormatNewsScript {
        t.Fatalf("NextOutputFormat(article) = %q, want news-script", got)
    }
    if got := PreviousOutputFormat(OutputFormatNewsScript); got != OutputFormatArticle {
        t.Fatalf("PreviousOutputFormat(news-script) = %q, want article", got)
    }
    if got := PreviousOutputFormat(OutputFormatArticle); got != OutputFormatPodcast {
        t.Fatalf("PreviousOutputFormat(article) = %q, want podcast", got)
    }
}

func TestDeveloperNewsPromptsDefaultToPodcastScript(t *testing.T) {
    wf := DefaultDeveloperNewsWorkflow("default")
    wf.Agent.Instructions = "Write actionable bullets."

    system := buildSystemPrompt(wf)
    user := buildUserPrompt(wf, []Item{{Title: "Test item"}})
    combined := system + "\n" + user

    for _, want := range []string{"Output format: podcast", "ポッドキャスト台本", "要約", "絵文字は使わない", "禁止:", "###", "読み原稿テンプレート", "まずは、", "Hook", "Insight", "Action", "事実・示唆・行動", "300文字以内", "ここで大事なのは", "解決策や次の動き", "明るい話題"} {
        if !strings.Contains(combined, want) {
            t.Fatalf("prompt missing %q:\n%s", want, combined)
        }
    }
    for _, bad := range []string{"一本目です。", "開発者への影響です。", "対応の目安です。", "解決策を探る時間です。", "テック系", "良い開発"} {
        if strings.Contains(developerNewsScriptTemplate(), bad) {
            t.Fatalf("prompt still contains stiff phrase %q:\n%s", bad, developerNewsScriptTemplate())
        }
    }
    if strings.Contains(system, "Write actionable bullets") {
        t.Fatalf("developer-news prompt included editable agent instructions:\n%s", system)
    }
    if !strings.Contains(user, "出力はポッドキャスト台本だけです") {
        t.Fatalf("user prompt does not end with strict script instruction:\n%s", user)
    }
}

func TestDeveloperNewsPromptsSupportSelectedOutputFormats(t *testing.T) {
    tests := []struct {
        format string
        want   []string
    }{
        {
            format: OutputFormatNewsScript,
            want:   []string{"Output format: news-script", "ニュース読み原稿", "ニュース原稿テンプレート", "まず押さえたいのは", "対応としては、", "出力はニュース読み原稿だけです"},
        },
        {
            format: OutputFormatArticle,
            want:   []string{"Output format: article", "読者が読む日本語のニュース記事本文", "記事テンプレート", "出力は記事本文だけです", "ニュース番組やポッドキャストの台本にしない"},
        },
        {
            format: OutputFormatPodcast,
            want:   []string{"Output format: podcast", "ニュースポッドキャスト台本", "読み原稿テンプレート", "出力はポッドキャスト台本だけです"},
        },
    }

    for _, tt := range tests {
        wf := DefaultDeveloperNewsWorkflow("default")
        wf.Agent.OutputFormat = tt.format
        combined := buildSystemPrompt(wf) + "\n" + buildUserPrompt(wf, []Item{{Title: "Test item"}})
        for _, want := range tt.want {
            if !strings.Contains(combined, want) {
                t.Fatalf("format %s prompt missing %q:\n%s", tt.format, want, combined)
            }
        }
    }
}

func TestShouldRewriteDeveloperNews(t *testing.T) {
    wf := DefaultDeveloperNewsWorkflow("default")
    bad := "以下は、2026年5月11日付のネットワーク・セキュリティ関連の最新研究動向の要約です。\n\n### 🔐 セキュリティとプライバシー\n\n* **6G量子耐性暗号の実装課題と新アーキテクチャ**"
    if !shouldRewriteDeveloperNews(bad, wf) {
        t.Fatal("expected markdown summary to trigger rewrite")
    }
    good := "今日のニュースです。\nまずは、生活への影響が大きいニュースです。"
    if shouldRewriteDeveloperNews(good, wf) {
        t.Fatal("did not expect spoken script to trigger rewrite")
    }
    spokenWithResearchTrend := "今日のニュースです。\nまずは、医療に関する重要な研究動向からです。"
    if shouldRewriteDeveloperNews(spokenWithResearchTrend, wf) {
        t.Fatal("did not expect spoken script with research-trend wording to trigger rewrite")
    }

    custom := Workflow{Label: "arxiv-security", Agent: AgentConfig{Enabled: true, Role: "rss summary agent"}}
    if !shouldRewriteDeveloperNews(bad, custom) {
        t.Fatal("expected custom enabled-agent workflow to trigger rewrite")
    }

    article := DefaultDeveloperNewsWorkflow("default")
    article.Agent.OutputFormat = OutputFormatArticle
    scriptShape := "今日のニュースです。\n\nまずは、重要な更新です。\n\n備えを進めつつ、新しい可能性にも目を向けましょう。"
    if !shouldRewriteDeveloperNews(scriptShape, article) {
        t.Fatal("expected podcast/script shape to trigger rewrite for article output")
    }
    articleShape := "今押さえたいニュース\n\n最初に見るべき影響の大きい動き\n重要な更新が公開されました。ここで重要なのは、前提を見直す必要がある点です。今日からは影響範囲を確認してください。"
    if shouldRewriteDeveloperNews(articleShape, article) {
        t.Fatalf("did not expect article shape to trigger rewrite:\n%s", articleShape)
    }
}

func TestFallbackDeveloperNewsScriptUsesStableTemplate(t *testing.T) {
    in := `今日のニュース、本日の主な項目です。
まずは、医療体制に関する重要な研究動向からです。
地域医療における新しい支援策の実証評価が進められています。
出典: https://arxiv.org/abs/2605.06881
以上、今日のニュースでした。`

    got := fallbackDeveloperNewsScript(in)
    if strings.Count(got, "今日のニュースです") != 1 {
        t.Fatalf("opening duplicated or missing:\n%s", got)
    }
    for _, want := range []string{"まずは、", "ここで大事なのは", "今日からは", "解決策や次の動き", "最後は、少し前向き"} {
        if !strings.Contains(got, want) {
            t.Fatalf("fallback missing template phrase %q:\n%s", want, got)
        }
    }
    for _, bad := range []string{"一本目です", "開発者への影響です。", "対応の目安です", "解決策を探る時間です", "良い開発"} {
        if strings.Contains(got, bad) {
            t.Fatalf("fallback contains stiff phrase %q:\n%s", bad, got)
        }
    }
    if strings.Contains(got, "出典:") || strings.Contains(got, "https://") {
        t.Fatalf("fallback should not include source lines:\n%s", got)
    }
}

func TestFallbackDeveloperNewsScriptRemovesMarkdownSummaryShape(t *testing.T) {
    in := `以下は、2026年5月11日付のネットワーク・セキュリティ関連の最新研究動向の要約です。

### 🔐 セキュリティとプライバシー

* **6G量子耐性暗号の実装課題と新アーキテクチャ**
    * **課題:** NIST標準化されたPQCを6G/IoTに導入する場合、署名サイズ拡大が帯域効率を低下させます。
    * [PQC評価](https://arxiv.org/abs/2605.06881)`

    got := fallbackDeveloperNewsScript(in)
    if shouldRewriteDeveloperNews(got, DefaultDeveloperNewsWorkflow("default")) {
        t.Fatalf("fallback still looks like markdown summary:\n%s", got)
    }
    for _, bad := range []string{"以下は", "###", "**", "🔐", "* "} {
        if strings.Contains(got, bad) {
            t.Fatalf("fallback contains %q:\n%s", bad, got)
        }
    }
    for _, want := range []string{"今日のニュースです", "解決策や次の動き", "備えを進めつつ"} {
        if !strings.Contains(got, want) {
            t.Fatalf("fallback missing %q:\n%s", want, got)
        }
    }
    if strings.Contains(got, "出典:") || strings.Contains(got, "https://") {
        t.Fatalf("fallback should not include source lines:\n%s", got)
    }
}

func TestFallbackDeveloperNewsOutputUsesSelectedFormat(t *testing.T) {
    in := `### セキュリティ更新
重大な脆弱性の修正が公開されました。
出典: https://example.com/news`

    news := DefaultDeveloperNewsWorkflow("default")
    news.Agent.OutputFormat = OutputFormatNewsScript
    newsGot := fallbackDeveloperNewsOutput(news, in)
    for _, want := range []string{"今日のニュースです。まず押さえたいのは", "ポイントは、", "最後は、少し前向きな話題です"} {
        if !strings.Contains(newsGot, want) {
            t.Fatalf("news-script fallback missing %q:\n%s", want, newsGot)
        }
    }
    for _, bad := range []string{"本日の主なトピックをお伝えします", "現場では、", "ここで重要なのは"} {
        if strings.Contains(newsGot, bad) {
            t.Fatalf("news-script fallback still contains stiff phrase %q:\n%s", bad, newsGot)
        }
    }

    article := DefaultDeveloperNewsWorkflow("default")
    article.Agent.OutputFormat = OutputFormatArticle
    articleGot := fallbackDeveloperNewsOutput(article, in)
    for _, want := range []string{"今押さえたいニュース", "影響の大きい動きから", "備えを進めながら"} {
        if !strings.Contains(articleGot, want) {
            t.Fatalf("article fallback missing %q:\n%s", want, articleGot)
        }
    }
    for _, bad := range []string{"今日のデベロッパーニュースです", "それでは、良い開発", "テック", "開発者", "https://"} {
        if strings.Contains(articleGot, bad) {
            t.Fatalf("article fallback contains %q:\n%s", bad, articleGot)
        }
    }
    if shouldRewriteDeveloperNews(articleGot, article) {
        t.Fatalf("article fallback still triggers rewrite:\n%s", articleGot)
    }
}

func TestDeveloperNewsTopicJudgeOrdersHardNewsAndBrightEnding(t *testing.T) {
    wf := DefaultDeveloperNewsWorkflow("default")
    wf.LLM.APIKeyEnv = "RSSFLOW_TEST_MISSING_API_KEY"
    items := []Item{
        {Title: "新しい開発ツールが安定版になりました", Description: "導入しやすくなった明るいニュースです。"},
        {Title: "重大な脆弱性が公開されました", Description: "広い利用者に影響する緊急度の高い問題です。"},
        {Title: "移行ガイドと緩和策が公開されました", Description: "影響を抑えるための具体策です。"},
    }

    calls := 0
    var draftRequest string
    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        calls++
        body, _ := io.ReadAll(r.Body)
        w.Header().Set("Content-Type", "application/json")
        if calls == 1 {
            if !strings.Contains(string(body), "編集判定器") {
                t.Fatalf("first request was not the topic judge:\n%s", body)
            }
            _, _ = w.Write([]byte(`{"choices":[{"message":{"role":"assistant","content":"{\"topics\":[{\"index\":1,\"score\":70,\"tone\":\"bright\",\"constructive\":false},{\"index\":2,\"score\":95,\"tone\":\"hard_negative\",\"constructive\":false},{\"index\":3,\"score\":80,\"tone\":\"constructive\",\"constructive\":true}]}"}}]}`))
            return
        }
        draftRequest = string(body)
        _, _ = w.Write([]byte(`{"choices":[{"message":{"role":"assistant","content":"今日のデベロッパーニュースです。現場の防衛から、次の開発につながるヒントまで厳選しました。\n\nまずは、重大な脆弱性が公開されました。\nここで大事なのは、これまでの防御策をそのまま信じられない段階に入ったことです。\n今日からは、修正版と影響範囲を確認しておきましょう。\n\n守りの次は、システムをより強くするための設計の話です。移行ガイドと緩和策を使うことで、影響を小さくできます。\nポイントは、後回しにせず検証を小さく始めることです。\n次のスプリントでは、検証環境で試すのが良さそうです。\n\n最後は、開発の未来が少し明るくなるニュースです。新しい開発ツールが安定版になりました。\n技術をどう使えば開発が楽になるのか、その視点で見ておきたい動きです。\n\n守りを固めつつ、新しい可能性に踏み出す。そんな一日にしていきましょう。それでは、良い開発を。"}}]}`))
    }))
    defer server.Close()

    wf.LLM.BaseURL = server.URL
    client, err := NewOpenAIClient(wf.LLM)
    if err != nil {
        t.Fatal(err)
    }
    if _, err := client.Summarize(context.Background(), wf, items); err != nil {
        t.Fatal(err)
    }
    if calls != 2 {
        t.Fatalf("calls = %d, want topic judge plus draft", calls)
    }
    hard := strings.Index(draftRequest, "重大な脆弱性が公開されました")
    constructive := strings.Index(draftRequest, "移行ガイドと緩和策が公開されました")
    bright := strings.Index(draftRequest, "新しい開発ツールが安定版になりました")
    if hard < 0 || constructive < 0 || bright < 0 {
        t.Fatalf("draft request missing reordered topics:\n%s", draftRequest)
    }
    if !(hard < constructive && constructive < bright) {
        t.Fatalf("topics not ordered hard, constructive, bright:\n%s", draftRequest)
    }
}

func TestDeveloperNewsInputIsCappedBeforeLLM(t *testing.T) {
    var items []Item
    for i := 0; i < 100; i++ {
        items = append(items, Item{
            Title:       "通常の更新",
            Description: strings.Repeat("説明", 400),
            SourceType:  "rss",
        })
    }
    items = append(items, Item{
        Title:       "重大な脆弱性 CVE-9999-0001 が公開されました",
        Description: strings.Repeat("セキュリティ", 120),
        SourceType:  "nvd",
    })

    candidates := prepareDeveloperNewsCandidateItems(items)
    if len(candidates) != developerNewsMaxCandidateItems {
        t.Fatalf("candidate len = %d, want %d", len(candidates), developerNewsMaxCandidateItems)
    }
    if !strings.Contains(candidates[0].Title, "重大な脆弱性") {
        t.Fatalf("important security item was not prioritized first: %#v", candidates[0])
    }
    for _, item := range candidates {
        if got := len([]rune(item.Description)); got > developerNewsPromptDescriptionSize+1 {
            t.Fatalf("description len = %d, want <= %d", got, developerNewsPromptDescriptionSize+1)
        }
    }

    scriptItems := limitDeveloperNewsScriptInputItems(candidates)
    if len(scriptItems) != developerNewsMaxScriptInputItems {
        t.Fatalf("script item len = %d, want %d", len(scriptItems), developerNewsMaxScriptInputItems)
    }
}

func TestDeveloperNewsInputKeepsSourceAndCategoryDiversity(t *testing.T) {
    var items []Item
    for i := 0; i < 50; i++ {
        items = append(items, Item{
            Title:       "重大な脆弱性 CVE-9999 が公開されました",
            Description: "security advisory",
            Source:      "https://security.example/feed.xml",
            SourceType:  "rss",
        })
    }
    for i := 0; i < 12; i++ {
        items = append(items, Item{
            Title:       "新しい安定版リリースが公開されました",
            Description: "release stable",
            Source:      "https://release.example/feed.xml",
            SourceType:  "rss",
        })
        items = append(items, Item{
            Title:       "Web標準化の新しい提案が進みました",
            Description: "standard proposal",
            Source:      "https://standards.example/feed.xml",
            SourceType:  "rss",
        })
        items = append(items, Item{
            Title:       "LLM開発ツールの改善が入りました",
            Description: "ai model tooling",
            Source:      "https://ai.example/feed.xml",
            SourceType:  "rss",
        })
    }

    candidates := prepareDeveloperNewsCandidateItems(items)
    if len(candidates) != developerNewsMaxCandidateItems {
        t.Fatalf("candidate len = %d, want %d", len(candidates), developerNewsMaxCandidateItems)
    }
    for _, want := range []string{"release", "standards", "ai"} {
        if !hasDeveloperNewsCategory(candidates, want) {
            t.Fatalf("candidates missing category %q:\n%#v", want, candidates)
        }
    }
    if count := countDeveloperNewsSource(candidates, "https://security.example/feed.xml"); count > diversityCap(developerNewsMaxCandidateItems, 3) {
        t.Fatalf("security source count = %d, want <= diversity cap", count)
    }
}

func TestDeveloperNewsScriptInputKeepsDiversityAfterRanking(t *testing.T) {
    var ranked []Item
    for i := 0; i < 20; i++ {
        ranked = append(ranked, Item{
            Title:      "重大な脆弱性の続報です",
            Source:     "https://security.example/feed.xml",
            SourceType: "rss",
        })
    }
    for _, item := range []Item{
        {Title: "新しい安定版リリースが公開されました", Source: "https://release.example/feed.xml", Description: "release stable"},
        {Title: "Web標準化の新しい提案が進みました", Source: "https://standards.example/feed.xml", Description: "standard proposal"},
        {Title: "LLM開発ツールの改善が入りました", Source: "https://ai.example/feed.xml", Description: "ai model tooling"},
    } {
        ranked = append(ranked, item)
    }

    got := limitDeveloperNewsScriptInputItems(ranked)
    if len(got) != developerNewsMaxScriptInputItems {
        t.Fatalf("script item len = %d, want %d", len(got), developerNewsMaxScriptInputItems)
    }
    for _, want := range []string{"release", "standards", "ai"} {
        if !hasDeveloperNewsCategory(got, want) {
            t.Fatalf("script input missing category %q:\n%#v", want, got)
        }
    }
}

func hasDeveloperNewsCategory(items []Item, category string) bool {
    for _, item := range items {
        if developerNewsCategory(item) == category {
            return true
        }
    }
    return false
}

func countDeveloperNewsSource(items []Item, source string) int {
    count := 0
    for _, item := range items {
        if developerNewsSourceKey(item) == source {
            count++
        }
    }
    return count
}

func TestDeveloperNewsTopicLimitUsesJapaneseCharacters(t *testing.T) {
    if got := japaneseScriptCharCount(strings.Repeat("あ", 300)); got != 300 {
        t.Fatalf("japanese char count = %d, want 300", got)
    }
    within := "今日のデベロッパーニュースです。\n\nまずは、" + strings.Repeat("あ", 280) + "。\n\n守りを固めつつ、新しい可能性に踏み出しましょう。"
    if developerNewsTopicsOverLimit(within, developerNewsTopicCharLimit) {
        t.Fatalf("topic within Japanese char limit was rejected")
    }
    over := "今日のデベロッパーニュースです。\n\nまずは、" + strings.Repeat("あ", 301) + "。\n\n守りを固めつつ、新しい可能性に踏み出しましょう。"
    if !developerNewsTopicsOverLimit(over, developerNewsTopicCharLimit) {
        t.Fatalf("topic over Japanese char limit was not rejected")
    }

    got := fallbackDeveloperNewsScript("### " + strings.Repeat("長いニュース", 120))
    for _, topic := range extractDeveloperNewsScriptTopics(got) {
        if count := japaneseScriptCharCount(topic); count > developerNewsTopicCharLimit {
            t.Fatalf("fallback topic has %d chars, want <= %d:\n%s", count, developerNewsTopicCharLimit, topic)
        }
    }
}

func TestFinalizeDeveloperNewsScriptStripsSourceLines(t *testing.T) {
    wf := DefaultDeveloperNewsWorkflow("default")
    client, err := NewOpenAIClient(wf.LLM)
    if err != nil {
        t.Fatal(err)
    }
    in := "今日のデベロッパーニュースです。\n\nまずは、重要な更新です。\nここで大事なのは、確認が必要になる点です。\n今日からは、検証を進めてください。\n出典: https://example.com/news\n\n最後は、開発の未来が少し明るくなるニュースです。改善も進んでいます。\n\n守りを固めつつ、新しい可能性に踏み出しましょう。"
    got, err := client.finalizeDeveloperNewsScript(context.Background(), wf, in)
    if err != nil {
        t.Fatal(err)
    }
    if strings.Contains(got, "出典") || strings.Contains(got, "https://") {
        t.Fatalf("final script still includes source:\n%s", got)
    }
}

func TestDeveloperNewsStreamUsesFinalizedSummaryOnly(t *testing.T) {
    wf := DefaultDeveloperNewsWorkflow("default")
    wf.Label = "arxiv-security"
    wf.Agent = AgentConfig{Enabled: true, Role: "rss summary agent", OutputLanguage: "Japanese"}
    wf.LLM.APIKeyEnv = "RSSFLOW_TEST_MISSING_API_KEY"
    bad := "以下は要約です。\n\n### 🔐 セキュリティ\n* **項目**\n* [Source](https://example.com/news)"
    calls := 0
    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        calls++
        w.Header().Set("Content-Type", "application/json")
        _, _ = w.Write([]byte(`{"choices":[{"message":{"role":"assistant","content":` + strconv.Quote(bad) + `}}]}`))
    }))
    defer server.Close()

    wf.LLM.BaseURL = server.URL
    client, err := NewOpenAIClient(wf.LLM)
    if err != nil {
        t.Fatal(err)
    }
    var delta string
    got, err := client.StreamSummarize(context.Background(), wf, []Item{{Title: "Test item"}}, func(s string) {
        delta += s
    })
    if err != nil {
        t.Fatal(err)
    }
    if calls != 3 {
        t.Fatalf("calls = %d, want topic judge plus first draft plus rewrite", calls)
    }
    if got != delta {
        t.Fatalf("delta did not receive finalized script:\ngot=%q\ndelta=%q", got, delta)
    }
    if shouldRewriteDeveloperNews(got, wf) {
        t.Fatalf("stream returned markdown summary shape:\n%s", got)
    }
}
```

## FILE: internal/rssflow/rss.go

```go
package rssflow

import (
    "context"
    "encoding/xml"
    "errors"
    "fmt"
    "io"
    "net/http"
    "strings"
    "time"
)

type Item struct {
    ID          string
    Title       string
    Link        string
    Description string
    Published   string
    Source      string
    SourceType  string
}

type rssFeed struct {
    Channel struct {
        Items []rssItem `xml:"item"`
    } `xml:"channel"`
}

type rssItem struct {
    GUID        string `xml:"guid"`
    Title       string `xml:"title"`
    Link        string `xml:"link"`
    Description string `xml:"description"`
    PubDate     string `xml:"pubDate"`
}

type atomFeed struct {
    Entries []atomItem `xml:"entry"`
}

type atomItem struct {
    ID      string     `xml:"id"`
    Title   string     `xml:"title"`
    Summary string     `xml:"summary"`
    Content string     `xml:"content"`
    Updated string     `xml:"updated"`
    Links   []atomLink `xml:"link"`
}

type atomLink struct {
    Href string `xml:"href,attr"`
    Rel  string `xml:"rel,attr"`
}

func FetchFeeds(ctx context.Context, urls []string, limit int) ([]Item, error) {
    if len(urls) == 0 {
        return nil, errors.New("no RSS URLs configured")
    }
    client := &http.Client{Timeout: 30 * time.Second}
    var items []Item
    var errs []string
    for _, u := range urls {
        got, err := fetchFeed(ctx, client, strings.TrimSpace(u))
        if err != nil {
            errs = append(errs, fmt.Sprintf("%s: %v", u, err))
            continue
        }
        items = append(items, got...)
        if limit > 0 && len(items) >= limit {
            return items[:limit], nil
        }
    }
    if len(items) == 0 && len(errs) > 0 {
        return nil, errors.New(strings.Join(errs, "; "))
    }
    return items, nil
}

func fetchFeed(ctx context.Context, client *http.Client, feedURL string) ([]Item, error) {
    if feedURL == "" {
        return nil, errors.New("empty feed URL")
    }
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, feedURL, nil)
    if err != nil {
        return nil, err
    }
    req.Header.Set("User-Agent", "rssflow/0.1")
    res, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer res.Body.Close()
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        return nil, fmt.Errorf("HTTP %d", res.StatusCode)
    }
    body, err := io.ReadAll(io.LimitReader(res.Body, 4<<20))
    if err != nil {
        return nil, err
    }
    return ParseFeed(body, feedURL)
}

func ParseFeed(body []byte, source string) ([]Item, error) {
    if got := parseRSS(body, source); len(got) > 0 {
        return got, nil
    }
    if got := parseAtom(body, source); len(got) > 0 {
        return got, nil
    }
    return nil, errors.New("no RSS/Atom items found")
}

func parseRSS(body []byte, source string) []Item {
    var feed rssFeed
    if err := xml.Unmarshal(body, &feed); err != nil {
        return nil
    }
    items := make([]Item, 0, len(feed.Channel.Items))
    for _, it := range feed.Channel.Items {
        link := strings.TrimSpace(it.Link)
        id := strings.TrimSpace(it.GUID)
        if id == "" {
            id = link
        }
        if id == "" {
            id = strings.TrimSpace(it.Title)
        }
        items = append(items, Item{
            ID:          id,
            Title:       strings.TrimSpace(it.Title),
            Link:        link,
            Description: compactText(it.Description),
            Published:   strings.TrimSpace(it.PubDate),
            Source:      source,
            SourceType:  "rss",
        })
    }
    return items
}

func parseAtom(body []byte, source string) []Item {
    var feed atomFeed
    if err := xml.Unmarshal(body, &feed); err != nil {
        return nil
    }
    items := make([]Item, 0, len(feed.Entries))
    for _, it := range feed.Entries {
        link := ""
        for _, l := range it.Links {
            if l.Rel == "" || l.Rel == "alternate" {
                link = strings.TrimSpace(l.Href)
                break
            }
        }
        desc := it.Summary
        if desc == "" {
            desc = it.Content
        }
        id := strings.TrimSpace(it.ID)
        if id == "" {
            id = link
        }
        items = append(items, Item{
            ID:          id,
            Title:       strings.TrimSpace(it.Title),
            Link:        link,
            Description: compactText(desc),
            Published:   strings.TrimSpace(it.Updated),
            Source:      source,
            SourceType:  "atom",
        })
    }
    return items
}

func compactText(s string) string {
    s = strings.ReplaceAll(s, "\n", " ")
    s = strings.ReplaceAll(s, "\t", " ")
    return strings.Join(strings.Fields(s), " ")
}
```

## FILE: internal/rssflow/rss_test.go

```go
package rssflow

import "testing"

func TestParseRSS(t *testing.T) {
    body := []byte(`<?xml version="1.0"?><rss><channel><item><guid>a</guid><title>A</title><link>https://example.com/a</link><description>Hello
world</description><pubDate>today</pubDate></item></channel></rss>`)
    items, err := ParseFeed(body, "feed")
    if err != nil {
        t.Fatal(err)
    }
    if len(items) != 1 {
        t.Fatalf("len = %d, want 1", len(items))
    }
    if items[0].Title != "A" || items[0].Description != "Hello world" {
        t.Fatalf("unexpected item: %+v", items[0])
    }
}

func TestParseAtom(t *testing.T) {
    body := []byte(`<?xml version="1.0"?><feed><entry><id>a</id><title>A</title><link href="https://example.com/a" rel="alternate"/><summary>Hi</summary><updated>now</updated></entry></feed>`)
    items, err := ParseFeed(body, "feed")
    if err != nil {
        t.Fatal(err)
    }
    if len(items) != 1 {
        t.Fatalf("len = %d, want 1", len(items))
    }
    if items[0].Link != "https://example.com/a" {
        t.Fatalf("link = %q", items[0].Link)
    }
}
```

## FILE: internal/rssflow/runner.go

```go
package rssflow

import (
    "context"
    "fmt"
    "strings"
)

type RunOptions struct {
    DryRun bool
    Force  bool
    Limit  int
}

type RunProgress struct {
    Stage   string
    Message string
    Topics  []RunProgressTopic
}

type RunProgressTopic struct {
    Rank  int
    Title string
    Score int
    Tone  string
}

type RunResult struct {
    Label      string
    Fetched    int
    NewItems   int
    Summary    string
    Items      []Item
    StateSaved bool
}

func RunWorkflow(ctx context.Context, wf Workflow, statePath string, opts RunOptions) (RunResult, error) {
    wf = NormalizeWorkflow(wf)
    limit := wf.RSS.Limit
    if opts.Limit > 0 {
        limit = opts.Limit
    }
    items, err := FetchWorkflowItems(ctx, wf, limit)
    if err != nil {
        return RunResult{}, err
    }
    st, err := LoadState(statePath)
    if err != nil {
        return RunResult{}, err
    }
    dedupe := effectiveDedupe(wf.Dedupe, opts)
    fresh, st := FilterNewItems(items, st, wf.Label, dedupe)
    result := RunResult{Label: wf.Label, Fetched: len(items), NewItems: len(fresh), Items: fresh}
    if len(fresh) == 0 {
        result.Summary = "No new items."
        return result, nil
    }
    if opts.DryRun {
        result.Summary = RenderItems(fresh)
        return result, nil
    }
    client, err := NewOpenAIClient(wf.LLM)
    if err != nil {
        return RunResult{}, err
    }
    summary, err := client.Summarize(ctx, wf, fresh)
    if err != nil {
        return RunResult{}, err
    }
    result.Summary = summary
    if dedupe.Enabled {
        if err := SaveState(statePath, st); err != nil {
            return RunResult{}, err
        }
        result.StateSaved = true
    }
    return result, nil
}

func RunWorkflowStream(ctx context.Context, wf Workflow, statePath string, opts RunOptions, onDelta func(string)) (RunResult, error) {
    return RunWorkflowStreamProgress(ctx, wf, statePath, opts, nil, onDelta)
}

func RunWorkflowStreamProgress(ctx context.Context, wf Workflow, statePath string, opts RunOptions, onProgress func(RunProgress), onDelta func(string)) (RunResult, error) {
    wf = NormalizeWorkflow(wf)
    limit := wf.RSS.Limit
    if opts.Limit > 0 {
        limit = opts.Limit
    }
    emitProgress(onProgress, "collect", fmt.Sprintf("collecting items from %d RSS feed(s) and %d configured source(s)", len(wf.RSS.URLs), CountConfiguredSources(wf.Sources)))
    items, err := FetchWorkflowItems(ctx, wf, limit)
    if err != nil {
        return RunResult{}, err
    }
    emitProgress(onProgress, "collect", fmt.Sprintf("collected %d item(s)", len(items)))
    emitProgress(onProgress, "state", "loading seen state")
    st, err := LoadState(statePath)
    if err != nil {
        return RunResult{}, err
    }
    emitProgress(onProgress, "filter", "removing duplicates and already-seen items")
    dedupe := effectiveDedupe(wf.Dedupe, opts)
    fresh, st := FilterNewItems(items, st, wf.Label, dedupe)
    result := RunResult{Label: wf.Label, Fetched: len(items), NewItems: len(fresh), Items: fresh}
    emitProgress(onProgress, "filter", fmt.Sprintf("%d new item(s) remain after filtering", len(fresh)))
    if len(fresh) == 0 {
        emitProgress(onProgress, "has-new", "condition: no new items; skip generation")
        result.Summary = "No new items."
        return result, nil
    }
    emitProgress(onProgress, "has-new", "condition: new items found; continue")
    if opts.DryRun {
        emitProgress(onProgress, "dry-run", "condition: dry-run enabled; skip LLM and state save")
        emitProgress(onProgress, "render", "dry run enabled; rendering filtered items without LLM")
        result.Summary = RenderItems(fresh)
        return result, nil
    }
    emitProgress(onProgress, "dry-run", "condition: live run; prepare LLM request")
    emitProgress(onProgress, "client", fmt.Sprintf("preparing LLM client for %s", wf.LLM.Model))
    client, err := NewOpenAIClient(wf.LLM)
    if err != nil {
        return RunResult{}, err
    }
    summary, err := client.StreamSummarizeProgress(ctx, wf, fresh, onProgress, onDelta)
    if err != nil {
        return RunResult{}, err
    }
    result.Summary = summary
    if !dedupe.Enabled {
        emitProgress(onProgress, "save-check", "condition: dedupe disabled; skip seen state save")
    }
    if dedupe.Enabled {
        emitProgress(onProgress, "save-check", "condition: dedupe enabled; persist seen state")
        emitProgress(onProgress, "save", "saving seen state")
        if err := SaveState(statePath, st); err != nil {
            return RunResult{}, err
        }
        result.StateSaved = true
    }
    emitProgress(onProgress, "done", "announcer read script is ready")
    return result, nil
}

func emitProgress(onProgress func(RunProgress), stage, message string, topics ...[]RunProgressTopic) {
    if onProgress != nil {
        progress := RunProgress{Stage: stage, Message: message}
        if len(topics) > 0 {
            progress.Topics = topics[0]
        }
        onProgress(progress)
    }
}

func effectiveDedupe(cfg DedupeConfig, opts RunOptions) DedupeConfig {
    if opts.Force {
        cfg.Enabled = false
    }
    return cfg
}

func RenderResult(result RunResult) string {
    var sb strings.Builder
    sb.WriteString(fmt.Sprintf("workflow: %s\n", result.Label))
    sb.WriteString(fmt.Sprintf("fetched: %d\n", result.Fetched))
    sb.WriteString(fmt.Sprintf("new_items: %d\n\n", result.NewItems))
    sb.WriteString(result.Summary)
    if !strings.HasSuffix(result.Summary, "\n") {
        sb.WriteString("\n")
    }
    return sb.String()
}

func RenderItems(items []Item) string {
    if len(items) == 0 {
        return "No new items."
    }
    var sb strings.Builder
    for i, item := range items {
        sb.WriteString(fmt.Sprintf("%d. %s\n", i+1, item.Title))
        if item.SourceType != "" || item.Source != "" {
            sb.WriteString("   " + strings.TrimSpace(item.SourceType+" "+item.Source) + "\n")
        }
        if item.Link != "" {
            sb.WriteString("   " + item.Link + "\n")
        }
        if item.Description != "" {
            sb.WriteString("   " + truncatePlain(item.Description, 180) + "\n")
        }
    }
    return sb.String()
}

func truncatePlain(s string, n int) string {
    runes := []rune(s)
    if len(runes) <= n {
        return s
    }
    if n <= 3 {
        return string(runes[:n])
    }
    return string(runes[:n-3]) + "..."
}
```

## FILE: internal/rssflow/sources.go

```go
package rssflow

import (
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "net/http"
    "net/url"
    "os"
    "strconv"
    "strings"
    "time"
)

const (
    defaultGitHubTokenEnv = "GITHUB_TOKEN"
    defaultNVDAPIKeyEnv   = "NVD_API_KEY"
    defaultSourceLimit    = 20
    defaultRepoItemLimit  = 5
    defaultAdvisoryLimit  = 30
    defaultNVDLimit       = 20
    defaultNVDDays        = 7
)

func FetchWorkflowItems(ctx context.Context, wf Workflow, limit int) ([]Item, error) {
    var items []Item
    var errs []string
    if len(wf.RSS.URLs) > 0 {
        got, err := FetchFeeds(ctx, wf.RSS.URLs, limit)
        if err != nil {
            errs = append(errs, err.Error())
        } else {
            items = append(items, got...)
        }
    }

    got, err := FetchSourceItems(ctx, wf.Sources, limit)
    if err != nil {
        errs = append(errs, err.Error())
    } else {
        items = append(items, got...)
    }

    if len(items) == 0 {
        if len(errs) > 0 {
            return nil, errors.New(strings.Join(errs, "; "))
        }
        return nil, errors.New("no input sources configured")
    }
    return items, nil
}

func FetchSourceItems(ctx context.Context, sources SourcesConfig, limit int) ([]Item, error) {
    if !hasConfiguredSources(sources) {
        return nil, nil
    }
    client := &http.Client{Timeout: 30 * time.Second}
    var items []Item
    var errs []string

    for _, repo := range sources.GitHub.Releases {
        got, err := fetchGitHubReleases(ctx, client, sources.GitHub, repo, sourceLimit(limit, defaultRepoItemLimit))
        if err != nil {
            errs = append(errs, fmt.Sprintf("github releases %s: %v", repo, err))
            continue
        }
        items = append(items, got...)
    }
    for _, repo := range sources.GitHub.Tags {
        got, err := fetchGitHubTags(ctx, client, sources.GitHub, repo, sourceLimit(limit, defaultRepoItemLimit))
        if err != nil {
            errs = append(errs, fmt.Sprintf("github tags %s: %v", repo, err))
            continue
        }
        items = append(items, got...)
    }
    if sources.GitHub.Advisories.Enabled {
        got, err := fetchGitHubAdvisories(ctx, client, sources.GitHub, sourceLimit(limit, advisoryLimit(sources.GitHub.Advisories)))
        if err != nil {
            errs = append(errs, fmt.Sprintf("github advisories: %v", err))
        } else {
            items = append(items, got...)
        }
    }

    for _, name := range sources.Packages.NPM {
        item, err := fetchNPMPackage(ctx, client, name)
        if err != nil {
            errs = append(errs, fmt.Sprintf("npm %s: %v", name, err))
            continue
        }
        items = append(items, item)
    }
    for _, name := range sources.Packages.PyPI {
        item, err := fetchPyPIPackage(ctx, client, name)
        if err != nil {
            errs = append(errs, fmt.Sprintf("pypi %s: %v", name, err))
            continue
        }
        items = append(items, item)
    }
    for _, name := range sources.Packages.Crates {
        item, err := fetchCrate(ctx, client, name)
        if err != nil {
            errs = append(errs, fmt.Sprintf("crates.io %s: %v", name, err))
            continue
        }
        items = append(items, item)
    }

    for _, keyword := range sources.Security.NVD.Keywords {
        got, err := fetchNVDKeyword(ctx, client, sources.Security.NVD, keyword, sourceLimit(limit, nvdLimit(sources.Security.NVD)))
        if err != nil {
            errs = append(errs, fmt.Sprintf("nvd %s: %v", keyword, err))
            continue
        }
        items = append(items, got...)
    }

    if len(items) == 0 && len(errs) > 0 {
        return nil, errors.New(strings.Join(errs, "; "))
    }
    return items, nil
}

func hasConfiguredSources(s SourcesConfig) bool {
    return len(s.GitHub.Releases) > 0 ||
        len(s.GitHub.Tags) > 0 ||
        s.GitHub.Advisories.Enabled ||
        len(s.Packages.NPM) > 0 ||
        len(s.Packages.PyPI) > 0 ||
        len(s.Packages.Crates) > 0 ||
        len(s.Security.NVD.Keywords) > 0
}

func CountConfiguredSources(s SourcesConfig) int {
    count := len(s.GitHub.Releases) +
        len(s.GitHub.Tags) +
        len(s.Packages.NPM) +
        len(s.Packages.PyPI) +
        len(s.Packages.Crates) +
        len(s.Security.NVD.Keywords)
    if s.GitHub.Advisories.Enabled {
        count++
    }
    return count
}

func sourceLimit(override, fallback int) int {
    if fallback <= 0 {
        fallback = defaultSourceLimit
    }
    if override > 0 && override < fallback {
        return override
    }
    return fallback
}

func advisoryLimit(cfg GitHubAdvisorySources) int {
    if cfg.Limit > 0 {
        return cfg.Limit
    }
    return defaultAdvisoryLimit
}

func nvdLimit(cfg NVDSources) int {
    if cfg.Limit > 0 {
        return cfg.Limit
    }
    return defaultNVDLimit
}

func fetchGitHubReleases(ctx context.Context, client *http.Client, cfg GitHubSources, repo string, limit int) ([]Item, error) {
    endpoint, err := githubRepoURL(repo, "releases")
    if err != nil {
        return nil, err
    }
    values := endpoint.Query()
    values.Set("per_page", strconv.Itoa(limit))
    endpoint.RawQuery = values.Encode()

    var releases []githubRelease
    if err := getJSON(ctx, client, endpoint.String(), githubHeaders(cfg), &releases); err != nil {
        return nil, err
    }
    return githubReleasesToItems(repo, releases), nil
}

func fetchGitHubTags(ctx context.Context, client *http.Client, cfg GitHubSources, repo string, limit int) ([]Item, error) {
    endpoint, err := githubRepoURL(repo, "tags")
    if err != nil {
        return nil, err
    }
    values := endpoint.Query()
    values.Set("per_page", strconv.Itoa(limit))
    endpoint.RawQuery = values.Encode()

    var tags []githubTag
    if err := getJSON(ctx, client, endpoint.String(), githubHeaders(cfg), &tags); err != nil {
        return nil, err
    }
    return githubTagsToItems(repo, tags), nil
}

func fetchGitHubAdvisories(ctx context.Context, client *http.Client, cfg GitHubSources, limit int) ([]Item, error) {
    advisories := cfg.Advisories
    ecosystems := nonEmptyOrDefault(advisories.Ecosystems, "")
    severities := nonEmptyOrDefault(advisories.Severities, "")
    seen := map[string]bool{}
    var items []Item
    for _, ecosystem := range ecosystems {
        for _, severity := range severities {
            endpoint, _ := url.Parse("https://api.github.com/advisories")
            values := endpoint.Query()
            values.Set("per_page", strconv.Itoa(limit))
            if ecosystem != "" {
                values.Set("ecosystem", ecosystem)
            }
            if severity != "" {
                values.Set("severity", severity)
            }
            endpoint.RawQuery = values.Encode()

            var got []githubAdvisory
            if err := getJSON(ctx, client, endpoint.String(), githubHeaders(cfg), &got); err != nil {
                return nil, err
            }
            for _, item := range githubAdvisoriesToItems(got) {
                if seen[item.ID] {
                    continue
                }
                seen[item.ID] = true
                items = append(items, item)
            }
        }
    }
    return items, nil
}

func fetchNPMPackage(ctx context.Context, client *http.Client, name string) (Item, error) {
    name = strings.TrimSpace(name)
    if name == "" {
        return Item{}, errors.New("empty package name")
    }
    endpoint := "https://registry.npmjs.org/" + url.PathEscape(name)
    var doc npmPackage
    if err := getJSON(ctx, client, endpoint, nil, &doc); err != nil {
        return Item{}, err
    }
    return npmPackageToItem(name, doc), nil
}

func fetchPyPIPackage(ctx context.Context, client *http.Client, name string) (Item, error) {
    name = strings.TrimSpace(name)
    if name == "" {
        return Item{}, errors.New("empty package name")
    }
    endpoint := "https://pypi.org/pypi/" + url.PathEscape(name) + "/json"
    var doc pyPIPackage
    if err := getJSON(ctx, client, endpoint, nil, &doc); err != nil {
        return Item{}, err
    }
    return pyPIPackageToItem(name, doc), nil
}

func fetchCrate(ctx context.Context, client *http.Client, name string) (Item, error) {
    name = strings.TrimSpace(name)
    if name == "" {
        return Item{}, errors.New("empty crate name")
    }
    endpoint := "https://crates.io/api/v1/crates/" + url.PathEscape(name)
    var doc cratesPackage
    if err := getJSON(ctx, client, endpoint, nil, &doc); err != nil {
        return Item{}, err
    }
    return crateToItem(name, doc), nil
}

func fetchNVDKeyword(ctx context.Context, client *http.Client, cfg NVDSources, keyword string, limit int) ([]Item, error) {
    keyword = strings.TrimSpace(keyword)
    if keyword == "" {
        return nil, nil
    }
    endpoint, _ := url.Parse("https://services.nvd.nist.gov/rest/json/cves/2.0")
    values := endpoint.Query()
    values.Set("keywordSearch", keyword)
    values.Set("resultsPerPage", strconv.Itoa(limit))
    days := cfg.Days
    if days <= 0 {
        days = defaultNVDDays
    }
    if days > 120 {
        days = 120
    }
    now := time.Now().UTC()
    values.Set("pubStartDate", now.AddDate(0, 0, -days).Format("2006-01-02T15:04:05.000"))
    values.Set("pubEndDate", now.Format("2006-01-02T15:04:05.000"))
    endpoint.RawQuery = values.Encode()

    headers := map[string]string{}
    apiKeyEnv := strings.TrimSpace(cfg.APIKeyEnv)
    if apiKeyEnv == "" {
        apiKeyEnv = defaultNVDAPIKeyEnv
    }
    if apiKey := strings.TrimSpace(os.Getenv(apiKeyEnv)); apiKey != "" {
        headers["apiKey"] = apiKey
    }

    var doc nvdResponse
    if err := getJSON(ctx, client, endpoint.String(), headers, &doc); err != nil {
        return nil, err
    }
    return nvdToItems(doc), nil
}

func getJSON(ctx context.Context, client *http.Client, endpoint string, headers map[string]string, out any) error {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
    if err != nil {
        return err
    }
    req.Header.Set("Accept", "application/json")
    req.Header.Set("User-Agent", "rssflow/0.1")
    for k, v := range headers {
        if strings.TrimSpace(v) != "" {
            req.Header.Set(k, v)
        }
    }
    res, err := client.Do(req)
    if err != nil {
        return err
    }
    defer res.Body.Close()
    body, err := io.ReadAll(io.LimitReader(res.Body, 4<<20))
    if err != nil {
        return err
    }
    if res.StatusCode < 200 || res.StatusCode >= 300 {
        return fmt.Errorf("HTTP %d: %s", res.StatusCode, truncateText(string(body), 180))
    }
    if err := json.Unmarshal(body, out); err != nil {
        return err
    }
    return nil
}

func githubHeaders(cfg GitHubSources) map[string]string {
    headers := map[string]string{
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    tokenEnv := strings.TrimSpace(cfg.TokenEnv)
    if tokenEnv == "" {
        tokenEnv = defaultGitHubTokenEnv
    }
    if token := strings.TrimSpace(os.Getenv(tokenEnv)); token != "" {
        headers["Authorization"] = "Bearer " + token
    }
    return headers
}

func githubRepoURL(repo, apiPath string) (*url.URL, error) {
    parts := strings.Split(strings.Trim(strings.TrimSpace(repo), "/"), "/")
    if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
        return nil, fmt.Errorf("repository must be owner/name")
    }
    endpoint, _ := url.Parse("https://api.github.com/repos/" + url.PathEscape(parts[0]) + "/" + url.PathEscape(parts[1]) + "/" + apiPath)
    return endpoint, nil
}

func githubWebURL(repo, suffix string) string {
    repo = strings.Trim(strings.TrimSpace(repo), "/")
    if repo == "" {
        return ""
    }
    return "https://github.com/" + repo + suffix
}

func nonEmptyOrDefault(values []string, fallback string) []string {
    out := make([]string, 0, len(values))
    for _, value := range values {
        value = strings.TrimSpace(value)
        if value != "" {
            out = append(out, value)
        }
    }
    if len(out) == 0 {
        return []string{fallback}
    }
    return out
}

type githubRelease struct {
    TagName     string `json:"tag_name"`
    Name        string `json:"name"`
    HTMLURL     string `json:"html_url"`
    Body        string `json:"body"`
    PublishedAt string `json:"published_at"`
    Prerelease  bool   `json:"prerelease"`
    Draft       bool   `json:"draft"`
}

type githubTag struct {
    Name   string `json:"name"`
    Commit struct {
        SHA string `json:"sha"`
    } `json:"commit"`
}

type githubAdvisory struct {
    GHSAID          string `json:"ghsa_id"`
    CVEID           string `json:"cve_id"`
    HTMLURL         string `json:"html_url"`
    URL             string `json:"url"`
    Summary         string `json:"summary"`
    Description     string `json:"description"`
    Severity        string `json:"severity"`
    PublishedAt     string `json:"published_at"`
    UpdatedAt       string `json:"updated_at"`
    Vulnerabilities []struct {
        Package struct {
            Ecosystem string `json:"ecosystem"`
            Name      string `json:"name"`
        } `json:"package"`
        VulnerableVersionRange string `json:"vulnerable_version_range"`
        FirstPatchedVersion    struct {
            Identifier string `json:"identifier"`
        } `json:"first_patched_version"`
    } `json:"vulnerabilities"`
}

func githubReleasesToItems(repo string, releases []githubRelease) []Item {
    items := make([]Item, 0, len(releases))
    for _, rel := range releases {
        if rel.Draft || strings.TrimSpace(rel.TagName) == "" {
            continue
        }
        title := "GitHub release: " + repo + " " + rel.TagName
        if strings.TrimSpace(rel.Name) != "" && rel.Name != rel.TagName {
            title += " - " + strings.TrimSpace(rel.Name)
        }
        descParts := []string{}
        if rel.Prerelease {
            descParts = append(descParts, "pre-release")
        }
        if strings.TrimSpace(rel.Body) != "" {
            descParts = append(descParts, rel.Body)
        }
        link := strings.TrimSpace(rel.HTMLURL)
        if link == "" {
            link = githubWebURL(repo, "/releases/tag/"+url.PathEscape(rel.TagName))
        }
        items = append(items, Item{
            ID:          "github-release:" + repo + ":" + rel.TagName,
            Title:       title,
            Link:        link,
            Description: truncateText(strings.Join(descParts, " "), 1400),
            Published:   rel.PublishedAt,
            Source:      "github:" + repo,
            SourceType:  "github_release",
        })
    }
    return items
}

func githubTagsToItems(repo string, tags []githubTag) []Item {
    items := make([]Item, 0, len(tags))
    for _, tag := range tags {
        if strings.TrimSpace(tag.Name) == "" {
            continue
        }
        desc := "Tag " + tag.Name
        if tag.Commit.SHA != "" {
            desc += " at commit " + tag.Commit.SHA
        }
        items = append(items, Item{
            ID:          "github-tag:" + repo + ":" + tag.Name,
            Title:       "GitHub tag: " + repo + " " + tag.Name,
            Link:        githubWebURL(repo, "/tree/"+url.PathEscape(tag.Name)),
            Description: desc,
            Source:      "github:" + repo,
            SourceType:  "github_tag",
        })
    }
    return items
}

func githubAdvisoriesToItems(advisories []githubAdvisory) []Item {
    items := make([]Item, 0, len(advisories))
    for _, adv := range advisories {
        id := firstNonEmpty(adv.GHSAID, adv.CVEID, adv.URL, adv.Summary)
        if id == "" {
            continue
        }
        title := "GitHub advisory"
        if adv.Severity != "" {
            title += " [" + adv.Severity + "]"
        }
        if adv.Summary != "" {
            title += ": " + adv.Summary
        }
        items = append(items, Item{
            ID:          "github-advisory:" + id,
            Title:       title,
            Link:        firstNonEmpty(adv.HTMLURL, adv.URL),
            Description: advisoryDescription(adv),
            Published:   firstNonEmpty(adv.PublishedAt, adv.UpdatedAt),
            Source:      "github:advisories",
            SourceType:  "github_advisory",
        })
    }
    return items
}

func advisoryDescription(adv githubAdvisory) string {
    parts := []string{}
    if adv.CVEID != "" {
        parts = append(parts, "CVE: "+adv.CVEID)
    }
    for _, vuln := range adv.Vulnerabilities {
        pkg := strings.TrimSpace(vuln.Package.Ecosystem + "/" + vuln.Package.Name)
        if pkg == "/" {
            continue
        }
        line := "Package: " + pkg
        if vuln.VulnerableVersionRange != "" {
            line += " affected " + vuln.VulnerableVersionRange
        }
        if vuln.FirstPatchedVersion.Identifier != "" {
            line += " patched " + vuln.FirstPatchedVersion.Identifier
        }
        parts = append(parts, line)
        if len(parts) >= 4 {
            break
        }
    }
    if adv.Description != "" {
        parts = append(parts, adv.Description)
    }
    return truncateText(strings.Join(parts, " "), 1400)
}

type npmPackage struct {
    Name        string                `json:"name"`
    Description string                `json:"description"`
    DistTags    map[string]string     `json:"dist-tags"`
    Time        map[string]string     `json:"time"`
    Versions    map[string]npmVersion `json:"versions"`
}

type npmVersion struct {
    Description  string         `json:"description"`
    Deprecated   any            `json:"deprecated"`
    Dependencies map[string]any `json:"dependencies"`
    Engines      map[string]any `json:"engines"`
}

func npmPackageToItem(name string, doc npmPackage) Item {
    version := firstNonEmpty(doc.DistTags["latest"])
    v := doc.Versions[version]
    desc := firstNonEmpty(v.Description, doc.Description)
    parts := []string{desc}
    if dep := deprecatedText(v.Deprecated); dep != "" {
        parts = append(parts, "deprecated: "+dep)
    }
    if len(v.Dependencies) > 0 {
        parts = append(parts, fmt.Sprintf("dependencies: %d", len(v.Dependencies)))
    }
    if len(v.Engines) > 0 {
        parts = append(parts, "engines: "+joinMapKeys(v.Engines))
    }
    return Item{
        ID:          "npm:" + name + ":" + version,
        Title:       "npm package: " + name + " " + version,
        Link:        "https://www.npmjs.com/package/" + url.PathEscape(name) + "/v/" + url.PathEscape(version),
        Description: truncateText(strings.Join(parts, " "), 1000),
        Published:   doc.Time[version],
        Source:      "npm:" + name,
        SourceType:  "package_npm",
    }
}

type pyPIPackage struct {
    Info struct {
        Name           string            `json:"name"`
        Version        string            `json:"version"`
        Summary        string            `json:"summary"`
        RequiresPython string            `json:"requires_python"`
        PackageURL     string            `json:"package_url"`
        ProjectURL     string            `json:"project_url"`
        ProjectURLs    map[string]string `json:"project_urls"`
    } `json:"info"`
    Releases map[string][]struct {
        UploadTimeISO8601 string `json:"upload_time_iso_8601"`
    } `json:"releases"`
}

func pyPIPackageToItem(name string, doc pyPIPackage) Item {
    version := doc.Info.Version
    parts := []string{doc.Info.Summary}
    if doc.Info.RequiresPython != "" {
        parts = append(parts, "requires-python: "+doc.Info.RequiresPython)
    }
    link := firstNonEmpty(doc.Info.PackageURL, doc.Info.ProjectURL, doc.Info.ProjectURLs["Homepage"], "https://pypi.org/project/"+url.PathEscape(name)+"/"+url.PathEscape(version)+"/")
    published := ""
    if releases := doc.Releases[version]; len(releases) > 0 {
        published = releases[0].UploadTimeISO8601
    }
    return Item{
        ID:          "pypi:" + name + ":" + version,
        Title:       "PyPI package: " + name + " " + version,
        Link:        link,
        Description: truncateText(strings.Join(parts, " "), 1000),
        Published:   published,
        Source:      "pypi:" + name,
        SourceType:  "package_pypi",
    }
}

type cratesPackage struct {
    Crate struct {
        ID            string `json:"id"`
        MaxVersion    string `json:"max_version"`
        NewestVersion string `json:"newest_version"`
        Description   string `json:"description"`
        UpdatedAt     string `json:"updated_at"`
        Documentation string `json:"documentation"`
        Repository    string `json:"repository"`
        Homepage      string `json:"homepage"`
    } `json:"crate"`
}

func crateToItem(name string, doc cratesPackage) Item {
    version := firstNonEmpty(doc.Crate.NewestVersion, doc.Crate.MaxVersion)
    link := "https://crates.io/crates/" + url.PathEscape(name) + "/" + url.PathEscape(version)
    parts := []string{doc.Crate.Description}
    if doc.Crate.Repository != "" {
        parts = append(parts, "repository: "+doc.Crate.Repository)
    }
    if doc.Crate.Documentation != "" {
        parts = append(parts, "docs: "+doc.Crate.Documentation)
    }
    return Item{
        ID:          "crates:" + name + ":" + version,
        Title:       "crates.io package: " + name + " " + version,
        Link:        link,
        Description: truncateText(strings.Join(parts, " "), 1000),
        Published:   doc.Crate.UpdatedAt,
        Source:      "crates:" + name,
        SourceType:  "package_crates",
    }
}

type nvdResponse struct {
    Vulnerabilities []struct {
        CVE nvdCVE `json:"cve"`
    } `json:"vulnerabilities"`
}

type nvdCVE struct {
    ID           string `json:"id"`
    Published    string `json:"published"`
    LastModified string `json:"lastModified"`
    Descriptions []struct {
        Lang  string `json:"lang"`
        Value string `json:"value"`
    } `json:"descriptions"`
    Metrics struct {
        CVSSMetricV31 []nvdMetric `json:"cvssMetricV31"`
        CVSSMetricV30 []nvdMetric `json:"cvssMetricV30"`
        CVSSMetricV2  []nvdMetric `json:"cvssMetricV2"`
    } `json:"metrics"`
    References []struct {
        URL    string `json:"url"`
        Source string `json:"source"`
    } `json:"references"`
}

type nvdMetric struct {
    CVSSData struct {
        BaseScore    float64 `json:"baseScore"`
        BaseSeverity string  `json:"baseSeverity"`
    } `json:"cvssData"`
    BaseSeverity string `json:"baseSeverity"`
}

func nvdToItems(doc nvdResponse) []Item {
    items := make([]Item, 0, len(doc.Vulnerabilities))
    for _, vuln := range doc.Vulnerabilities {
        cve := vuln.CVE
        if cve.ID == "" {
            continue
        }
        severity, score := nvdSeverity(cve)
        title := "NVD CVE: " + cve.ID
        if severity != "" {
            title += " [" + severity + "]"
        }
        parts := []string{englishDescription(cve)}
        if score > 0 {
            parts = append(parts, fmt.Sprintf("CVSS: %.1f", score))
        }
        if len(cve.References) > 0 && cve.References[0].URL != "" {
            parts = append(parts, "reference: "+cve.References[0].URL)
        }
        items = append(items, Item{
            ID:          "nvd:" + cve.ID,
            Title:       title,
            Link:        "https://nvd.nist.gov/vuln/detail/" + cve.ID,
            Description: truncateText(strings.Join(parts, " "), 1400),
            Published:   firstNonEmpty(cve.Published, cve.LastModified),
            Source:      "nvd",
            SourceType:  "nvd_cve",
        })
    }
    return items
}

func nvdSeverity(cve nvdCVE) (string, float64) {
    metrics := [][]nvdMetric{cve.Metrics.CVSSMetricV31, cve.Metrics.CVSSMetricV30, cve.Metrics.CVSSMetricV2}
    for _, group := range metrics {
        if len(group) == 0 {
            continue
        }
        metric := group[0]
        severity := firstNonEmpty(metric.CVSSData.BaseSeverity, metric.BaseSeverity)
        return severity, metric.CVSSData.BaseScore
    }
    return "", 0
}

func englishDescription(cve nvdCVE) string {
    for _, desc := range cve.Descriptions {
        if desc.Lang == "en" && strings.TrimSpace(desc.Value) != "" {
            return desc.Value
        }
    }
    if len(cve.Descriptions) > 0 {
        return cve.Descriptions[0].Value
    }
    return ""
}

func deprecatedText(value any) string {
    switch v := value.(type) {
    case string:
        return strings.TrimSpace(v)
    case bool:
        if v {
            return "true"
        }
    }
    return ""
}

func joinMapKeys(values map[string]any) string {
    keys := make([]string, 0, len(values))
    for key := range values {
        keys = append(keys, key)
    }
    return strings.Join(keys, ", ")
}

func firstNonEmpty(values ...string) string {
    for _, value := range values {
        if strings.TrimSpace(value) != "" {
            return strings.TrimSpace(value)
        }
    }
    return ""
}

func truncateText(s string, n int) string {
    s = compactText(s)
    if len(s) <= n {
        return s
    }
    if n <= 3 {
        return s[:n]
    }
    return s[:n-3] + "..."
}
```

## FILE: internal/rssflow/sources_test.go

```go
package rssflow

import "testing"

func TestDefaultDeveloperNewsWorkflowConfiguresNonRSSSources(t *testing.T) {
    wf := DefaultDeveloperNewsWorkflow("default")
    if wf.Label != "developer-news-agent" {
        t.Fatalf("label = %q", wf.Label)
    }
    if got := CountConfiguredSources(wf.Sources); got == 0 {
        t.Fatal("expected non-RSS sources")
    }
    if !wf.Agent.Enabled || wf.Agent.Role == "" || wf.Agent.Instructions == "" {
        t.Fatalf("missing agent defaults: %+v", wf.Agent)
    }
}

func TestGitHubReleasesToItems(t *testing.T) {
    items := githubReleasesToItems("owner/repo", []githubRelease{{
        TagName:     "v1.2.3",
        Name:        "Release v1.2.3",
        HTMLURL:     "https://github.com/owner/repo/releases/tag/v1.2.3",
        Body:        "Fixes a security issue.",
        PublishedAt: "2026-05-01T00:00:00Z",
    }})
    if len(items) != 1 {
        t.Fatalf("len = %d, want 1", len(items))
    }
    if items[0].ID != "github-release:owner/repo:v1.2.3" {
        t.Fatalf("id = %q", items[0].ID)
    }
    if items[0].SourceType != "github_release" {
        t.Fatalf("source type = %q", items[0].SourceType)
    }
}

func TestPackageConverters(t *testing.T) {
    npm := npmPackageToItem("react", npmPackage{
        Description: "ui library",
        DistTags:    map[string]string{"latest": "19.1.0"},
        Time:        map[string]string{"19.1.0": "2026-05-01T00:00:00.000Z"},
        Versions: map[string]npmVersion{
            "19.1.0": {Dependencies: map[string]any{"loose-envify": "^1.1.0"}},
        },
    })
    if npm.ID != "npm:react:19.1.0" || npm.SourceType != "package_npm" {
        t.Fatalf("unexpected npm item: %+v", npm)
    }

    pypi := pyPIPackageToItem("fastapi", pyPIPackage{})
    if pypi.SourceType != "package_pypi" {
        t.Fatalf("source type = %q", pypi.SourceType)
    }

    crate := crateToItem("serde", cratesPackage{})
    if crate.SourceType != "package_crates" {
        t.Fatalf("source type = %q", crate.SourceType)
    }
}

func TestNVDToItems(t *testing.T) {
    doc := nvdResponse{Vulnerabilities: []struct {
        CVE nvdCVE `json:"cve"`
    }{{
        CVE: nvdCVE{
            ID:        "CVE-2026-0001",
            Published: "2026-05-01T00:00:00.000",
            Descriptions: []struct {
                Lang  string `json:"lang"`
                Value string `json:"value"`
            }{{Lang: "en", Value: "Example vulnerability."}},
        },
    }}}
    items := nvdToItems(doc)
    if len(items) != 1 {
        t.Fatalf("len = %d, want 1", len(items))
    }
    if items[0].ID != "nvd:CVE-2026-0001" || items[0].SourceType != "nvd_cve" {
        t.Fatalf("unexpected nvd item: %+v", items[0])
    }
}
```

## FILE: internal/tui/model.go

```go
package tui

import (
    "context"
    "fmt"
    "io"
    "os"
    "strconv"
    "strings"
    "time"

    "github.com/atotto/clipboard"
    osc52 "github.com/aymanbagabas/go-osc52/v2"
    "github.com/charmbracelet/bubbles/textinput"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
    "github.com/tik-choco/rssflow/internal/rssflow"
)

type mode int

const (
    modeList mode = iota
    modeEdit
    modeModels
    modeProfiles
    modeProfileEdit
    modeTest
)

type model struct {
    configPath       string
    config           *rssflow.Config
    width            int
    height           int
    index            int
    mode             mode
    fields           []textinput.Model
    profileFields    []textinput.Model
    focus            int
    profileFocus     int
    editOffset       int
    info             string
    err              error
    models           []string
    modelIndex       int
    modelReturn      mode
    profileIndex     int
    profileReturn    mode
    resultOutput     string
    resultDraft      string
    resultMessages   []runChatMessage
    resultDryRun     bool
    resultForce      bool
    resultLLMTest    bool
    resultStreamTest bool
    resultDone       bool
    resultOffset     int
    runFlow          []runFlowNode
    runFlowPhase     int
    runFlowOffset    int
    selectedRunFlow  int
    runDetailOpen    bool
    runDetailOffset  int
    runStageLogs     map[string][]string
    rankingStage     string
    rankingTopics    []runRankTopic
    streamCh         chan streamMsg
}

const (
    fieldLabel = iota
    fieldURLs
    fieldLimit
    fieldDedupe
    fieldMaxSeen
    fieldAPIKeyEnv
    fieldBaseURL
    fieldLLMProfile
    fieldModel
    fieldMaxTokens
    fieldTemperature
    fieldAgent
    fieldAgentRole
    fieldAgentLanguage
    fieldOutputFormat
    fieldAgentInstructions
    fieldCount
)

var labels = []string{
    "Label", "RSS URLs (comma separated)", "RSS limit", "Dedupe enabled", "Dedupe max seen",
    "OpenAI API key env", "OpenAI base URL", "LLM profile", "OpenAI model", "Max tokens", "Temperature",
    "Agent enabled", "Agent role", "Output language", "Output format", "Agent instructions",
}

var workflowFields = []int{
    fieldLabel,
    fieldURLs,
    fieldLimit,
    fieldDedupe,
    fieldMaxSeen,
    fieldLLMProfile,
    fieldModel,
    fieldAgent,
    fieldAgentRole,
    fieldAgentLanguage,
    fieldOutputFormat,
    fieldAgentInstructions,
}

const (
    profileFieldLabel = iota
    profileFieldAPIKeyEnv
    profileFieldBaseURL
    profileFieldModel
    profileFieldMaxTokens
    profileFieldTemperature
    profileFieldCount
)

var profileLabels = []string{
    "Label", "API key env", "Base URL", "Model", "Max tokens", "Temperature",
}

func Run(configPath string) error {
    cfg, err := rssflow.LoadConfig(configPath)
    if err != nil {
        return err
    }
    if len(cfg.LLMProfiles) == 0 {
        cfg.LLMProfiles = []rssflow.LLMProfile{rssflow.DefaultLLMProfile()}
    }
    if len(cfg.Workflows) == 0 {
        wf := rssflow.DefaultWorkflow()
        wf.LLM = rssflow.LLMConfig{Provider: "openai", Profile: cfg.LLMProfiles[0].Label}
        cfg.Workflows = []rssflow.Workflow{wf}
    }
    m := newModel(configPath, cfg)
    _, err = tea.NewProgram(m, tea.WithAltScreen()).Run()
    return err
}

func newModel(configPath string, cfg *rssflow.Config) *model {
    fields := make([]textinput.Model, fieldCount)
    for i := range fields {
        fields[i] = textinput.New()
        fields[i].Width = 72
        fields[i].CharLimit = 4096
    }
    profileFields := make([]textinput.Model, profileFieldCount)
    for i := range profileFields {
        profileFields[i] = textinput.New()
        profileFields[i].Width = 72
        profileFields[i].CharLimit = 4096
    }
    fields[fieldAgentInstructions].Width = 96
    fields[fieldOutputFormat].Width = 24
    m := &model{configPath: configPath, config: cfg, fields: fields, profileFields: profileFields, width: 100, height: 36}
    m.loadFields()
    return m
}

func (m *model) Init() tea.Cmd { return nil }

func (m *model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case modelsMsg:
        m.models = msg.models
        m.err = msg.err
        m.mode = modeModels
        m.modelIndex = m.indexOfModel(m.currentModelValue())
        return m, nil
    case testMsg:
        m.resultOutput = msg.output
        m.resultDryRun = msg.dryRun
        m.resultForce = msg.force
        m.resultLLMTest = msg.llmTest
        m.resultStreamTest = msg.streamTest
        m.resultDone = true
        m.err = msg.err
        m.mode = modeTest
        return m, nil
    case streamMsg:
        m.resultDryRun = msg.dryRun
        m.resultForce = msg.force
        m.resultLLMTest = msg.llmTest
        m.resultStreamTest = msg.streamTest
        if msg.progressStage != "" {
            m.advanceRunFlow(msg.progressStage, msg.chatText)
            m.rankingStage = msg.progressStage
            m.appendRunStageLog(msg.progressStage, msg.chatText)
        }
        if len(msg.progressTopics) > 0 {
            m.rankingTopics = runRankTopicsFromProgress(msg.progressTopics)
        }
        if msg.chatText != "" {
            role := msg.chatRole
            if role == "" {
                role = "system"
            }
            m.resultMessages = append(m.resultMessages, runChatMessage{Role: role, Text: msg.chatText})
            m.followResult()
        }
        if msg.output != "" {
            m.resultOutput += msg.output
            if !m.resultLLMTest {
                m.resultDraft += msg.output
            }
            m.followResult()
        }
        if msg.draftDelta != "" {
            m.resultDraft += msg.draftDelta
            m.resultOutput = m.resultDraft
            m.followResult()
        }
        if msg.err != nil {
            m.err = msg.err
            m.failRunFlow(msg.err.Error())
        }
        if msg.done {
            m.resultDone = true
            if msg.err == nil {
                m.completeRunFlow()
            }
            if msg.finalOutput != "" {
                if m.resultLLMTest {
                    m.resultOutput = msg.finalOutput
                } else {
                    m.resultDraft = msg.finalOutput
                    m.resultOutput = msg.finalOutput
                }
                m.followResult()
            }
            return m, nil
        }
        return m, m.waitStreamCmd()
    case flowTickMsg:
        if m.mode == modeTest && !m.resultDone && !m.resultLLMTest {
            m.runFlowPhase++
            return m, m.flowTickCmd()
        }
        return m, nil
    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height
        m.setInputWidths()
        return m, nil
    case tea.KeyMsg:
        return m.handleKey(msg)
    }
    if m.mode == modeEdit {
        var cmd tea.Cmd
        m.fields[m.focus], cmd = m.fields[m.focus].Update(msg)
        return m, cmd
    }
    return m, nil
}

func (m *model) View() string {
    switch m.mode {
    case modeEdit:
        return m.viewEdit()
    case modeModels:
        return m.viewModels()
    case modeProfiles:
        return m.viewProfiles()
    case modeProfileEdit:
        return m.viewProfileEdit()
    case modeTest:
        return m.viewTest()
    default:
        return m.viewList()
    }
}

func (m *model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch m.mode {
    case modeEdit:
        return m.handleEditKey(msg)
    case modeModels:
        return m.handleModelsKey(msg)
    case modeProfiles:
        return m.handleProfilesKey(msg)
    case modeProfileEdit:
        return m.handleProfileEditKey(msg)
    case modeTest:
        switch msg.String() {
        case "esc", "q":
            if !m.resultLLMTest && m.runDetailOpen {
                m.runDetailOpen = false
                return m, nil
            }
            m.mode = modeList
        case "enter":
            if !m.resultLLMTest {
                m.runDetailOpen = !m.runDetailOpen
                m.runDetailOffset = 0
            }
        case "up", "k":
            if !m.resultLLMTest && m.runDetailOpen {
                if m.runDetailOffset > 0 {
                    m.runDetailOffset--
                }
            } else if !m.resultLLMTest {
                m.moveRunFlowSelection(-m.runFlowColumns())
            } else if m.resultOffset > 0 {
                m.resultOffset--
            }
        case "down", "j":
            if !m.resultLLMTest && m.runDetailOpen {
                m.runDetailOffset++
                m.clampRunDetailOffset()
            } else if !m.resultLLMTest {
                m.moveRunFlowSelection(m.runFlowColumns())
            } else {
                m.resultOffset++
                m.clampResultOffset()
            }
        case "left", "h":
            if !m.resultLLMTest && !m.runDetailOpen {
                m.moveRunFlowSelection(-1)
            }
        case "right", "l":
            if !m.resultLLMTest && !m.runDetailOpen {
                m.moveRunFlowSelection(1)
            }
        case "pgup":
            if !m.resultLLMTest && m.runDetailOpen {
                m.runDetailOffset -= m.runDetailVisibleLines()
                if m.runDetailOffset < 0 {
                    m.runDetailOffset = 0
                }
            } else if !m.resultLLMTest {
                m.runFlowOffset -= m.runFlowVisibleLines()
                if m.runFlowOffset < 0 {
                    m.runFlowOffset = 0
                }
            } else {
                m.resultOffset -= m.resultVisibleLines()
                if m.resultOffset < 0 {
                    m.resultOffset = 0
                }
            }
        case "pgdown":
            if !m.resultLLMTest && m.runDetailOpen {
                m.runDetailOffset += m.runDetailVisibleLines()
                m.clampRunDetailOffset()
            } else if !m.resultLLMTest {
                m.runFlowOffset += m.runFlowVisibleLines()
                m.clampRunFlowOffset()
            } else {
                m.resultOffset += m.resultVisibleLines()
                m.clampResultOffset()
            }
        case "home":
            if !m.resultLLMTest && m.runDetailOpen {
                m.runDetailOffset = 0
            } else if !m.resultLLMTest {
                m.runFlowOffset = 0
                m.selectedRunFlow = 0
            } else {
                m.resultOffset = 0
            }
        case "end":
            if !m.resultLLMTest && m.runDetailOpen {
                m.followRunDetail()
            } else if !m.resultLLMTest {
                m.selectedRunFlow = len(m.runFlow) - 1
                m.followRunFlow()
            } else {
                m.followResult()
            }
        case "c", "C", "y":
            text := m.copyableResultText()
            if text == "" {
                m.err = nil
                m.info = "no manuscript to copy yet"
                return m, nil
            }
            m.err = nil
            m.info = "copying manuscript to clipboard"
            return m, copyManuscriptCmd(text)
        }
        return m, nil
    default:
        return m.handleListKey(msg)
    }
}

func (m *model) handleListKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch msg.String() {
    case "ctrl+c", "q":
        return m, tea.Quit
    case "up", "k":
        if m.index > 0 {
            m.index--
        }
    case "down", "j":
        if m.index < len(m.config.Workflows)-1 {
            m.index++
        }
    case "a":
        m.config.Workflows = append(m.config.Workflows, m.defaultWorkflow())
        m.index = len(m.config.Workflows) - 1
        m.loadFields()
        m.mode = modeEdit
    case "A":
        m.upsertDeveloperNewsWorkflow()
        m.loadFields()
        m.save()
    case "e", "enter":
        m.loadFields()
        m.mode = modeEdit
    case "d":
        if len(m.config.Workflows) > 1 {
            m.config.Workflows = append(m.config.Workflows[:m.index], m.config.Workflows[m.index+1:]...)
            if m.index >= len(m.config.Workflows) {
                m.index = len(m.config.Workflows) - 1
            }
            m.save()
        }
    case "s":
        m.save()
    case "m":
        return m.openModels(modeList)
    case "p":
        m.profileReturn = modeList
        m.mode = modeProfiles
    case "L":
        m.startLLMTest()
        return m, m.llmTestCmd()
    case "S":
        m.startLLMStreamTest()
        return m, m.startLLMStreamTestCmd()
    case "r":
        m.startResult(false, false)
        return m, m.startStreamCmd(false, false)
    case "R":
        m.startResult(false, true)
        return m, m.startStreamCmd(false, true)
    case "t":
        m.startResult(true, false)
        return m, m.startStreamCmd(true, false)
    case "T":
        m.startResult(true, true)
        return m, m.startStreamCmd(true, true)
    }
    return m, nil
}

func (m *model) handleEditKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch msg.String() {
    case "esc":
        m.mode = modeList
        return m, nil
    case "ctrl+s":
        if err := m.applyFields(); err != nil {
            m.err = err
        } else {
            m.save()
            m.mode = modeList
        }
        return m, nil
    case "enter":
        if m.focus == fieldModel {
            return m.openModels(modeEdit)
        }
        if m.focus == fieldLLMProfile {
            return m.openProfiles(modeEdit)
        }
        if m.focus == fieldOutputFormat {
            m.fields[fieldOutputFormat].SetValue(rssflow.NextOutputFormat(m.fields[fieldOutputFormat].Value()))
            m.info = "output format: " + rssflow.OutputFormatLabel(m.fields[fieldOutputFormat].Value())
            return m, nil
        }
    case "left", "h":
        if m.focus == fieldOutputFormat {
            m.fields[fieldOutputFormat].SetValue(rssflow.PreviousOutputFormat(m.fields[fieldOutputFormat].Value()))
            m.info = "output format: " + rssflow.OutputFormatLabel(m.fields[fieldOutputFormat].Value())
            return m, nil
        }
    case "right", "l":
        if m.focus == fieldOutputFormat {
            m.fields[fieldOutputFormat].SetValue(rssflow.NextOutputFormat(m.fields[fieldOutputFormat].Value()))
            m.info = "output format: " + rssflow.OutputFormatLabel(m.fields[fieldOutputFormat].Value())
            return m, nil
        }
    case "ctrl+o":
        if m.focus == fieldModel {
            return m.openModels(modeEdit)
        }
        return m.openProfiles(modeEdit)
    case "tab", "down":
        m.focus = m.nextWorkflowField()
        m.ensureEditFocusVisible()
        return m, m.updateFocus()
    case "shift+tab", "up":
        m.focus = m.previousWorkflowField()
        m.ensureEditFocusVisible()
        return m, m.updateFocus()
    }
    var cmd tea.Cmd
    m.fields[m.focus], cmd = m.fields[m.focus].Update(msg)
    m.ensureEditFocusVisible()
    return m, cmd
}

func (m *model) handleModelsKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch msg.String() {
    case "esc", "q":
        m.mode = m.modelReturn
    case "up", "k":
        if m.modelIndex > 0 {
            m.modelIndex--
        }
    case "down", "j":
        if m.modelIndex < len(m.models)-1 {
            m.modelIndex++
        }
    case "enter":
        if len(m.models) > 0 {
            selected := m.models[m.modelIndex]
            switch m.modelReturn {
            case modeEdit:
                m.fields[fieldModel].SetValue(selected)
                m.mode = modeEdit
            case modeProfileEdit:
                m.profileFields[profileFieldModel].SetValue(selected)
                m.mode = modeProfileEdit
            default:
                m.setSelectedWorkflowModel(selected)
                m.save()
                m.mode = modeList
            }
        }
    }
    return m, nil
}

func (m *model) handleProfilesKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch msg.String() {
    case "esc", "q":
        m.mode = m.profileReturn
    case "up", "k":
        if m.profileIndex > 0 {
            m.profileIndex--
        }
    case "down", "j":
        if m.profileIndex < len(m.config.LLMProfiles)-1 {
            m.profileIndex++
        }
    case "a":
        m.config.LLMProfiles = append(m.config.LLMProfiles, rssflow.DefaultLLMProfile())
        m.profileIndex = len(m.config.LLMProfiles) - 1
        m.loadProfileFields()
        m.mode = modeProfileEdit
    case "e":
        m.loadProfileFields()
        m.mode = modeProfileEdit
    case "d":
        if len(m.config.LLMProfiles) > 1 {
            m.config.LLMProfiles = append(m.config.LLMProfiles[:m.profileIndex], m.config.LLMProfiles[m.profileIndex+1:]...)
            if m.profileIndex >= len(m.config.LLMProfiles) {
                m.profileIndex = len(m.config.LLMProfiles) - 1
            }
            m.save()
        }
    case "enter":
        if m.profileReturn == modeEdit && len(m.config.LLMProfiles) > 0 {
            profile := m.config.LLMProfiles[m.profileIndex]
            m.fields[fieldLLMProfile].SetValue(profile.Label)
            m.mode = modeEdit
        } else {
            m.loadProfileFields()
            m.mode = modeProfileEdit
        }
    }
    return m, nil
}

func (m *model) handleProfileEditKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch msg.String() {
    case "esc":
        m.mode = modeProfiles
        return m, nil
    case "ctrl+s":
        if err := m.applyProfileFields(); err != nil {
            m.err = err
        } else {
            m.save()
            m.mode = modeProfiles
        }
        return m, nil
    case "enter":
        if m.profileFocus == profileFieldModel {
            return m.openModels(modeProfileEdit)
        }
    case "ctrl+o":
        return m.openModels(modeProfileEdit)
    case "tab", "down":
        m.profileFocus = (m.profileFocus + 1) % profileFieldCount
        return m, m.updateProfileFocus()
    case "shift+tab", "up":
        m.profileFocus = (m.profileFocus - 1 + profileFieldCount) % profileFieldCount
        return m, m.updateProfileFocus()
    }
    var cmd tea.Cmd
    m.profileFields[m.profileFocus], cmd = m.profileFields[m.profileFocus].Update(msg)
    return m, cmd
}

func (m *model) loadFields() {
    raw := rssflow.NormalizeWorkflow(m.config.Workflows[m.index])
    wf := rssflow.ResolveWorkflow(m.config, raw)
    profile := raw.LLM.Profile
    if profile == "" {
        profile = m.defaultProfileLabel()
    }
    values := []string{
        wf.Label,
        strings.Join(wf.RSS.URLs, ", "),
        strconv.Itoa(wf.RSS.Limit),
        strconv.FormatBool(wf.Dedupe.Enabled),
        strconv.Itoa(wf.Dedupe.MaxSeen),
        wf.LLM.APIKeyEnv,
        wf.LLM.BaseURL,
        profile,
        wf.LLM.Model,
        strconv.Itoa(wf.LLM.MaxTokens),
        fmt.Sprintf("%.2f", wf.LLM.Temperature),
        strconv.FormatBool(wf.Agent.Enabled),
        wf.Agent.Role,
        wf.Agent.OutputLanguage,
        rssflow.NormalizeOutputFormat(wf.Agent.OutputFormat),
        wf.Agent.Instructions,
    }
    for i := range values {
        m.fields[i].SetValue(values[i])
    }
    m.focus = 0
    m.updateFocus()
}

func (m *model) applyFields() error {
    limit, err := strconv.Atoi(strings.TrimSpace(m.fields[fieldLimit].Value()))
    if err != nil {
        return fmt.Errorf("invalid RSS limit")
    }
    maxSeen, err := strconv.Atoi(strings.TrimSpace(m.fields[fieldMaxSeen].Value()))
    if err != nil {
        return fmt.Errorf("invalid max seen")
    }
    profile := strings.TrimSpace(m.fields[fieldLLMProfile].Value())
    if profile == "" {
        return fmt.Errorf("LLM profile is required")
    }
    model := strings.TrimSpace(m.fields[fieldModel].Value())
    if model == "" {
        return fmt.Errorf("model is required")
    }
    existing := m.config.Workflows[m.index]
    llm := existing.LLM
    llm.Provider = "openai"
    llm.Profile = profile
    llm.Model = model
    wf := rssflow.Workflow{
        Label: strings.TrimSpace(m.fields[fieldLabel].Value()),
        RSS: rssflow.RSSSettings{
            URLs:  splitCSV(m.fields[fieldURLs].Value()),
            Limit: limit,
        },
        Sources: existing.Sources,
        Dedupe: rssflow.DedupeConfig{
            Enabled: parseBool(m.fields[fieldDedupe].Value()),
            MaxSeen: maxSeen,
        },
        LLM: llm,
        Agent: rssflow.AgentConfig{
            Enabled:        parseBool(m.fields[fieldAgent].Value()),
            Role:           strings.TrimSpace(m.fields[fieldAgentRole].Value()),
            OutputLanguage: strings.TrimSpace(m.fields[fieldAgentLanguage].Value()),
            OutputFormat:   rssflow.NormalizeOutputFormat(m.fields[fieldOutputFormat].Value()),
            Instructions:   strings.TrimSpace(m.fields[fieldAgentInstructions].Value()),
        },
    }
    if wf.Label == "" {
        return fmt.Errorf("label is required")
    }
    if len(wf.RSS.URLs) == 0 {
        return fmt.Errorf("at least one RSS URL is required")
    }
    m.config.Workflows[m.index] = rssflow.NormalizeWorkflow(wf)
    return nil
}

func (m *model) updateFocus() tea.Cmd {
    cmds := make([]tea.Cmd, len(m.fields))
    for i := range m.fields {
        if i == m.focus {
            cmds[i] = m.fields[i].Focus()
        } else {
            m.fields[i].Blur()
        }
    }
    return tea.Batch(cmds...)
}

func (m *model) updateProfileFocus() tea.Cmd {
    cmds := make([]tea.Cmd, len(m.profileFields))
    for i := range m.profileFields {
        if i == m.profileFocus {
            cmds[i] = m.profileFields[i].Focus()
        } else {
            m.profileFields[i].Blur()
        }
    }
    return tea.Batch(cmds...)
}

func (m *model) setInputWidths() {
    width := m.contentWidth() - 8
    if width < 28 {
        width = 28
    }
    if width > 96 {
        width = 96
    }
    for i := range m.fields {
        m.fields[i].Width = width
    }
    for i := range m.profileFields {
        m.profileFields[i].Width = width
    }
}

func (m *model) contentWidth() int {
    width := m.width - 4
    if width < 72 {
        width = 72
    }
    if width > 120 {
        width = 120
    }
    return width
}

func (m *model) save() {
    m.err = rssflow.SaveConfig(m.configPath, m.config)
    if m.err == nil {
        m.info = "saved: " + m.configPath
    }
}

func (m *model) openModels(returnMode mode) (tea.Model, tea.Cmd) {
    m.modelReturn = returnMode
    m.mode = modeModels
    m.models = nil
    m.modelIndex = 0
    m.err = nil
    m.info = ""
    return m, m.fetchModelsCmd(m.workflowForModelFetch(returnMode))
}

func (m *model) openProfiles(returnMode mode) (tea.Model, tea.Cmd) {
    m.profileReturn = returnMode
    m.mode = modeProfiles
    m.profileIndex = m.indexOfProfile(strings.TrimSpace(m.fields[fieldLLMProfile].Value()))
    m.err = nil
    m.info = ""
    return m, nil
}

func (m *model) defaultWorkflow() rssflow.Workflow {
    wf := rssflow.DefaultWorkflow()
    wf.LLM = rssflow.LLMConfig{Provider: "openai", Profile: m.defaultProfileLabel()}
    return wf
}

func (m *model) upsertDeveloperNewsWorkflow() {
    wf := rssflow.DefaultDeveloperNewsWorkflow(m.defaultProfileLabel())
    for i := range m.config.Workflows {
        if m.config.Workflows[i].Label == wf.Label {
            m.config.Workflows[i] = wf
            m.index = i
            return
        }
    }
    m.config.Workflows = append(m.config.Workflows, wf)
    m.index = len(m.config.Workflows) - 1
}

func (m *model) defaultProfileLabel() string {
    if len(m.config.LLMProfiles) == 0 {
        return ""
    }
    return m.config.LLMProfiles[0].Label
}

func (m *model) workflowForModelFetch(returnMode mode) rssflow.Workflow {
    switch returnMode {
    case modeEdit:
        wf := m.config.Workflows[m.index]
        wf.LLM.Provider = "openai"
        wf.LLM.APIKeyEnv = strings.TrimSpace(m.fields[fieldAPIKeyEnv].Value())
        wf.LLM.BaseURL = strings.TrimSpace(m.fields[fieldBaseURL].Value())
        wf.LLM.Profile = strings.TrimSpace(m.fields[fieldLLMProfile].Value())
        wf.LLM.Model = strings.TrimSpace(m.fields[fieldModel].Value())
        return rssflow.ResolveWorkflow(m.config, wf)
    case modeProfileEdit:
        return rssflow.Workflow{
            LLM: rssflow.NormalizeLLMConfig(rssflow.LLMConfig{
                Provider:  "openai",
                APIKeyEnv: strings.TrimSpace(m.profileFields[profileFieldAPIKeyEnv].Value()),
                BaseURL:   strings.TrimSpace(m.profileFields[profileFieldBaseURL].Value()),
                Model:     strings.TrimSpace(m.profileFields[profileFieldModel].Value()),
            }),
        }
    default:
        return rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
    }
}

func (m *model) currentModelValue() string {
    switch m.modelReturn {
    case modeEdit:
        return strings.TrimSpace(m.fields[fieldModel].Value())
    case modeProfileEdit:
        return strings.TrimSpace(m.profileFields[profileFieldModel].Value())
    default:
        wf := rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
        return strings.TrimSpace(wf.LLM.Model)
    }
}

func (m *model) indexOfModel(model string) int {
    for i, candidate := range m.models {
        if candidate == model {
            return i
        }
    }
    return 0
}

func (m *model) indexOfProfile(label string) int {
    for i, profile := range m.config.LLMProfiles {
        if profile.Label == label {
            return i
        }
    }
    return 0
}

func (m *model) setSelectedWorkflowModel(model string) {
    profileLabel := m.config.Workflows[m.index].LLM.Profile
    if profileLabel != "" {
        if i := m.indexOfProfile(profileLabel); i >= 0 && i < len(m.config.LLMProfiles) && m.config.LLMProfiles[i].Label == profileLabel {
            m.config.LLMProfiles[i].Model = model
            return
        }
    }
    m.config.Workflows[m.index].LLM.Model = model
}

func (m *model) loadProfileFields() {
    profile := rssflow.NormalizeLLMProfile(m.config.LLMProfiles[m.profileIndex])
    values := []string{
        profile.Label,
        profile.APIKeyEnv,
        profile.BaseURL,
        profile.Model,
        strconv.Itoa(profile.MaxTokens),
        fmt.Sprintf("%.2f", profile.Temperature),
    }
    for i := range values {
        m.profileFields[i].SetValue(values[i])
    }
    m.profileFocus = 0
    m.updateProfileFocus()
}

func (m *model) applyProfileFields() error {
    maxTokens, err := strconv.Atoi(strings.TrimSpace(m.profileFields[profileFieldMaxTokens].Value()))
    if err != nil {
        return fmt.Errorf("invalid profile max tokens")
    }
    temp, err := strconv.ParseFloat(strings.TrimSpace(m.profileFields[profileFieldTemperature].Value()), 64)
    if err != nil {
        return fmt.Errorf("invalid profile temperature")
    }
    profile := rssflow.LLMProfile{
        Label:       strings.TrimSpace(m.profileFields[profileFieldLabel].Value()),
        Provider:    "openai",
        APIKeyEnv:   strings.TrimSpace(m.profileFields[profileFieldAPIKeyEnv].Value()),
        BaseURL:     strings.TrimSpace(m.profileFields[profileFieldBaseURL].Value()),
        Model:       strings.TrimSpace(m.profileFields[profileFieldModel].Value()),
        MaxTokens:   maxTokens,
        Temperature: temp,
    }
    if profile.Label == "" {
        return fmt.Errorf("profile label is required")
    }
    m.config.LLMProfiles[m.profileIndex] = rssflow.NormalizeLLMProfile(profile)
    return nil
}

func (m *model) fetchModelsCmd(wf rssflow.Workflow) tea.Cmd {
    return func() tea.Msg {
        client, err := rssflow.NewOpenAIClient(wf.LLM)
        if err != nil {
            return modelsMsg{err: err}
        }
        ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
        defer cancel()
        models, err := client.ListModels(ctx)
        return modelsMsg{models: models, err: err}
    }
}

func (m *model) startResult(dryRun bool, force bool) {
    m.mode = modeTest
    m.err = nil
    m.resultOutput = ""
    m.resultDraft = ""
    m.resultMessages = nil
    m.resultDryRun = dryRun
    m.resultForce = force
    m.resultLLMTest = false
    m.resultStreamTest = false
    m.resultDone = false
    m.resultOffset = 0
    m.runFlow = newRunFlow()
    m.runFlowPhase = 0
    m.runFlowOffset = 0
    m.selectedRunFlow = 0
    m.runDetailOpen = false
    m.runDetailOffset = 0
    m.runStageLogs = map[string][]string{}
    m.rankingStage = ""
    m.rankingTopics = nil
    m.streamCh = make(chan streamMsg, 64)
}

func (m *model) startLLMTest() {
    m.mode = modeTest
    m.err = nil
    m.resultOutput = ""
    m.resultDraft = ""
    m.resultMessages = nil
    m.resultDryRun = false
    m.resultForce = false
    m.resultLLMTest = true
    m.resultStreamTest = false
    m.resultDone = false
    m.resultOffset = 0
    m.runFlow = nil
    m.rankingStage = ""
    m.rankingTopics = nil
}

func (m *model) startLLMStreamTest() {
    m.mode = modeTest
    m.err = nil
    m.resultOutput = ""
    m.resultDraft = ""
    m.resultMessages = nil
    m.resultDryRun = false
    m.resultForce = false
    m.resultLLMTest = true
    m.resultStreamTest = true
    m.resultDone = false
    m.resultOffset = 0
    m.runFlow = nil
    m.rankingStage = ""
    m.rankingTopics = nil
    m.streamCh = make(chan streamMsg, 64)
}

func (m *model) llmTestCmd() tea.Cmd {
    wf := rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
    return func() tea.Msg {
        client, err := rssflow.NewOpenAIClient(wf.LLM)
        if err != nil {
            return testMsg{llmTest: true, err: err}
        }
        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()
        output, err := client.Ping(ctx, wf.LLM)
        if err != nil {
            return testMsg{llmTest: true, err: err}
        }
        return testMsg{
            llmTest: true,
            output:  fmt.Sprintf("LLM ping OK\n\nprofile: %s\nmodel: %s\nbase_url: %s\n\nresponse:\n%s\n", m.config.Workflows[m.index].LLM.Profile, wf.LLM.Model, wf.LLM.BaseURL, output),
        }
    }
}

func (m *model) startLLMStreamTestCmd() tea.Cmd {
    wf := rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
    ch := m.streamCh
    return tea.Batch(func() tea.Msg {
        go llmStreamTestToChannel(ch, wf)
        return nil
    }, m.waitStreamCmd())
}

func (m *model) startStreamCmd(dryRun bool, force bool) tea.Cmd {
    wf := rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
    ch := m.streamCh
    return tea.Batch(func() tea.Msg {
        go runWorkflowToChannel(ch, wf, dryRun, force)
        return nil
    }, m.waitStreamCmd(), m.flowTickCmd())
}

func (m *model) flowTickCmd() tea.Cmd {
    return tea.Tick(180*time.Millisecond, func(time.Time) tea.Msg {
        return flowTickMsg{}
    })
}

func (m *model) waitStreamCmd() tea.Cmd {
    ch := m.streamCh
    return func() tea.Msg {
        if ch == nil {
            return nil
        }
        msg, ok := <-ch
        if !ok {
            return streamMsg{dryRun: m.resultDryRun, force: m.resultForce, done: true}
        }
        return msg
    }
}

func runWorkflowToChannel(ch chan<- streamMsg, wf rssflow.Workflow, dryRun bool, force bool) {
    defer close(ch)
    statePath, err := rssflow.StatePath()
    if err != nil {
        ch <- streamMsg{dryRun: dryRun, force: force, done: true, err: err}
        return
    }
    ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
    defer cancel()
    ch <- streamMsg{dryRun: dryRun, force: force, progressStage: "start", chatRole: "you", chatText: fmt.Sprintf("Run %s", wf.Label)}
    result, err := rssflow.RunWorkflowStreamProgress(ctx, wf, statePath, rssflow.RunOptions{DryRun: dryRun, Force: force}, func(progress rssflow.RunProgress) {
        ch <- streamMsg{dryRun: dryRun, force: force, progressStage: progress.Stage, progressTopics: progress.Topics, chatRole: "agent", chatText: progress.Message}
    }, func(delta string) {
        ch <- streamMsg{dryRun: dryRun, force: force, draftDelta: delta}
    })
    if err != nil {
        ch <- streamMsg{dryRun: dryRun, force: force, done: true, err: err}
        return
    }
    ch <- streamMsg{
        dryRun:        dryRun,
        force:         force,
        done:          true,
        finalOutput:   result.Summary,
        progressStage: "done",
        chatRole:      "agent",
        chatText:      fmt.Sprintf("fetched %d item(s), kept %d new item(s). announcer script ready.", result.Fetched, result.NewItems),
    }
}

func llmStreamTestToChannel(ch chan<- streamMsg, wf rssflow.Workflow) {
    defer close(ch)
    client, err := rssflow.NewOpenAIClient(wf.LLM)
    if err != nil {
        ch <- streamMsg{llmTest: true, streamTest: true, done: true, err: err}
        return
    }
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    ch <- streamMsg{llmTest: true, streamTest: true, output: fmt.Sprintf("LLM streaming ping\n\nprofile: %s\nmodel: %s\nbase_url: %s\n\nresponse:\n", wf.LLM.Profile, wf.LLM.Model, wf.LLM.BaseURL)}
    chunkCount := 0
    output, err := client.StreamPing(ctx, wf.LLM, func(delta string) {
        chunkCount++
        ch <- streamMsg{llmTest: true, streamTest: true, output: delta}
    })
    if err != nil {
        ch <- streamMsg{llmTest: true, streamTest: true, done: true, err: err}
        return
    }
    ch <- streamMsg{llmTest: true, streamTest: true, done: true, output: fmt.Sprintf("\n\nchunks: %d\nfinal: %s\n", chunkCount, output)}
}

func (m *model) followResult() {
    text := m.resultOutput
    if !m.resultLLMTest {
        text = m.runChatText(m.contentWidth() - 8)
    }
    lines := strings.Count(text, "\n") + 1
    visible := m.resultVisibleLines()
    m.resultOffset = lines - visible
    if m.resultOffset < 0 {
        m.resultOffset = 0
    }
}

func (m *model) clampResultOffset() {
    text := m.resultOutput
    if !m.resultLLMTest {
        text = m.runChatText(m.contentWidth() - 8)
    }
    lines := strings.Count(text, "\n") + 1
    maxOffset := lines - m.resultVisibleLines()
    if maxOffset < 0 {
        maxOffset = 0
    }
    if m.resultOffset > maxOffset {
        m.resultOffset = maxOffset
    }
}

func (m *model) followRunFlow() {
    lines := strings.Count(m.runFlowGraph(m.runFlowPanelInnerWidth()), "\n") + 1
    maxOffset := lines - m.runFlowVisibleLines()
    if maxOffset < 0 {
        maxOffset = 0
    }
    m.runFlowOffset = maxOffset
}

func (m *model) clampRunFlowOffset() {
    lines := strings.Count(m.runFlowGraph(m.runFlowPanelInnerWidth()), "\n") + 1
    maxOffset := lines - m.runFlowVisibleLines()
    if maxOffset < 0 {
        maxOffset = 0
    }
    if m.runFlowOffset > maxOffset {
        m.runFlowOffset = maxOffset
    }
}

func (m *model) moveRunFlowSelection(delta int) {
    if len(m.runFlow) == 0 {
        return
    }
    m.selectedRunFlow += delta
    if m.selectedRunFlow < 0 {
        m.selectedRunFlow = 0
    }
    if m.selectedRunFlow >= len(m.runFlow) {
        m.selectedRunFlow = len(m.runFlow) - 1
    }
    m.ensureRunFlowSelectionVisible()
}

func (m *model) ensureRunFlowSelectionVisible() {
    cols := m.runFlowColumns()
    if cols <= 0 {
        cols = 1
    }
    row := m.selectedRunFlow / cols
    line := row * 6
    visible := m.runFlowVisibleLines()
    if line < m.runFlowOffset {
        m.runFlowOffset = line
    }
    if line+5 >= m.runFlowOffset+visible {
        m.runFlowOffset = line + 6 - visible
    }
    if m.runFlowOffset < 0 {
        m.runFlowOffset = 0
    }
    m.clampRunFlowOffset()
}

func (m *model) runFlowColumns() int {
    width := m.runFlowPanelInnerWidth()
    switch {
    case width >= 92:
        return 4
    case width >= 72:
        return 3
    case width >= 46:
        return 2
    default:
        return 1
    }
}

func (m *model) appendRunStageLog(stage, text string) {
    if stage == "" || text == "" {
        return
    }
    if m.runStageLogs == nil {
        m.runStageLogs = map[string][]string{}
    }
    m.runStageLogs[stage] = append(m.runStageLogs[stage], text)
}

func (m *model) followRunDetail() {
    lines := strings.Count(m.runDetailText(m.runFlowPanelInnerWidth()), "\n") + 1
    maxOffset := lines - m.runDetailVisibleLines()
    if maxOffset < 0 {
        maxOffset = 0
    }
    m.runDetailOffset = maxOffset
}

func (m *model) clampRunDetailOffset() {
    lines := strings.Count(m.runDetailText(m.runFlowPanelInnerWidth()), "\n") + 1
    maxOffset := lines - m.runDetailVisibleLines()
    if maxOffset < 0 {
        maxOffset = 0
    }
    if m.runDetailOffset > maxOffset {
        m.runDetailOffset = maxOffset
    }
}

func (m *model) runDetailVisibleLines() int {
    height := m.height - 16
    if height < 8 {
        return 8
    }
    return height
}

func (m *model) runFlowVisibleLines() int {
    height := m.height - 16
    if height < 8 {
        return 8
    }
    return height
}

func (m *model) runFlowPanelInnerWidth() int {
    width := m.contentWidth() - 20
    if width < 44 {
        width = 44
    }
    return width
}

func (m *model) copyableResultText() string {
    if strings.TrimSpace(m.resultDraft) != "" {
        return strings.TrimSpace(m.resultDraft)
    }
    return strings.TrimSpace(m.resultOutput)
}

func copyTextOSC52Cmd(text string) tea.Cmd {
    return func() tea.Msg {
        writeOSC52(text, os.Stdout)
        return nil
    }
}

func copyManuscriptCmd(text string) tea.Cmd {
    return tea.Batch(copyClipboardCmd(text), copyTextOSC52Cmd(text))
}

func copyClipboardCmd(text string) tea.Cmd {
    return func() tea.Msg {
        _ = clipboard.WriteAll(text)
        return nil
    }
}

func writeOSC52(text string, out io.Writer) {
    if out == nil {
        return
    }
    seq := osc52.New(text)
    term := strings.ToLower(os.Getenv("TERM"))
    switch {
    case os.Getenv("TMUX") != "":
        seq = seq.Tmux()
    case strings.Contains(term, "screen"):
        seq = seq.Screen()
    }
    _, _ = seq.WriteTo(out)
}

func (m *model) resultVisibleLines() int {
    height := m.height - 9
    if !m.resultLLMTest && len(m.runFlow) > 0 {
        height -= 7
    }
    if height < 8 {
        return 8
    }
    return height
}

func (m *model) ensureEditFocusVisible() {
    line := m.fieldLine(m.focus)
    visible := m.editVisibleLines()
    if line < m.editOffset {
        m.editOffset = line
    }
    if line >= m.editOffset+visible {
        m.editOffset = line - visible + 1
    }
    if m.editOffset < 0 {
        m.editOffset = 0
    }
}

func (m *model) fieldLine(field int) int {
    line := 0
    for i := 0; i < m.visibleWorkflowFieldIndex(field); i++ {
        line += 3
    }
    return line
}

func (m *model) nextWorkflowField() int {
    index := m.visibleWorkflowFieldIndex(m.focus)
    return workflowFields[(index+1)%len(workflowFields)]
}

func (m *model) previousWorkflowField() int {
    index := m.visibleWorkflowFieldIndex(m.focus)
    return workflowFields[(index-1+len(workflowFields))%len(workflowFields)]
}

func (m *model) visibleWorkflowFieldIndex(field int) int {
    for i, candidate := range workflowFields {
        if candidate == field {
            return i
        }
    }
    return 0
}

func (m *model) editVisibleLines() int {
    height := m.height - 6
    if height < 10 {
        return 10
    }
    return height
}

func splitCSV(s string) []string {
    var out []string
    for _, part := range strings.Split(s, ",") {
        part = strings.TrimSpace(part)
        if part != "" {
            out = append(out, part)
        }
    }
    return out
}

func parseBool(s string) bool {
    switch strings.ToLower(strings.TrimSpace(s)) {
    case "true", "t", "1", "yes", "y", "on":
        return true
    default:
        return false
    }
}

type modelsMsg struct {
    models []string
    err    error
}

type runChatMessage struct {
    Role string
    Text string
}

type testMsg struct {
    output     string
    dryRun     bool
    force      bool
    llmTest    bool
    streamTest bool
    err        error
}

type streamMsg struct {
    output         string
    draftDelta     string
    finalOutput    string
    progressStage  string
    progressTopics []rssflow.RunProgressTopic
    chatRole       string
    chatText       string
    dryRun         bool
    force          bool
    llmTest        bool
    streamTest     bool
    done           bool
    err            error
}

type flowTickMsg struct{}

type runFlowStatus int

const (
    runFlowPending runFlowStatus = iota
    runFlowActive
    runFlowDone
    runFlowSkipped
    runFlowError
)

type runFlowNode struct {
    Stage       string
    Label       string
    Description string
    Detail      string
    Kind        string
    Status      runFlowStatus
}

type runRankTopic struct {
    Rank  int
    Title string
    Score int
    Tone  string
}

func newRunFlow() []runFlowNode {
    return []runFlowNode{
        {Stage: "start", Label: "Start", Description: "workflow selected", Status: runFlowActive},
        {Stage: "collect", Label: "Collect feeds", Description: "RSS and configured sources", Status: runFlowPending},
        {Stage: "state", Label: "Load state", Description: "read seen item cache", Status: runFlowPending},
        {Stage: "filter", Label: "Filter items", Description: "dedupe and force rules", Status: runFlowPending},
        {Stage: "has-new", Label: "New items?", Description: "branch on remaining items", Kind: "condition", Status: runFlowPending},
        {Stage: "dry-run", Label: "Dry run?", Description: "branch around LLM call", Kind: "condition", Status: runFlowPending},
        {Stage: "render", Label: "Render list", Description: "dry-run output path", Status: runFlowPending},
        {Stage: "client", Label: "Prepare LLM", Description: "API profile and model", Status: runFlowPending},
        {Stage: "candidate", Label: "Pick candidates", Description: "trim and diversify topic pool", Status: runFlowPending},
        {Stage: "score", Label: "Score topics", Description: "LLM editorial judgment", Status: runFlowPending},
        {Stage: "sort", Label: "Sort by score", Description: "highest impact first", Status: runFlowPending},
        {Stage: "arc", Label: "Arrange arc", Description: "serious lead, useful middle, bright close", Status: runFlowPending},
        {Stage: "limit", Label: "Limit input", Description: "final topics sent to writer", Status: runFlowPending},
        {Stage: "generate", Label: "Generate", Description: "stream summary/script", Status: runFlowPending},
        {Stage: "save-check", Label: "Save state?", Description: "branch on dedupe setting", Kind: "condition", Status: runFlowPending},
        {Stage: "save", Label: "Save state", Description: "persist seen items", Status: runFlowPending},
        {Stage: "done", Label: "Done", Description: "final output ready", Status: runFlowPending},
    }
}

func (m *model) advanceRunFlow(stage, detail string) {
    if len(m.runFlow) == 0 {
        return
    }
    index := m.runFlowIndex(stage)
    if index < 0 {
        return
    }
    switch stage {
    case "render":
        m.skipRunFlowStages("client", "candidate", "score", "sort", "arc", "limit", "generate", "save-check", "save")
    case "client":
        m.skipRunFlowStages("render")
    case "generate":
        m.skipRunFlowStages("candidate", "score", "sort", "arc", "limit")
    case "done":
        m.skipPendingRunFlowBefore(index)
    }
    for i := 0; i < index; i++ {
        if m.runFlow[i].Status == runFlowPending || m.runFlow[i].Status == runFlowActive {
            m.runFlow[i].Status = runFlowDone
        }
    }
    m.runFlow[index].Status = runFlowActive
    if detail != "" {
        m.runFlow[index].Detail = detail
    }
}

func runRankTopicsFromProgress(topics []rssflow.RunProgressTopic) []runRankTopic {
    out := make([]runRankTopic, 0, len(topics))
    for _, topic := range topics {
        out = append(out, runRankTopic{
            Rank:  topic.Rank,
            Title: topic.Title,
            Score: topic.Score,
            Tone:  topic.Tone,
        })
    }
    return out
}

func (m *model) completeRunFlow() {
    if len(m.runFlow) == 0 {
        return
    }
    done := m.runFlowIndex("done")
    for i := range m.runFlow {
        switch {
        case i < done && m.runFlow[i].Status == runFlowPending:
            m.runFlow[i].Status = runFlowSkipped
        case i <= done && m.runFlow[i].Status == runFlowActive:
            m.runFlow[i].Status = runFlowDone
        }
    }
    if done >= 0 {
        m.runFlow[done].Status = runFlowDone
    }
}

func (m *model) skipRunFlowStages(stages ...string) {
    for _, stage := range stages {
        index := m.runFlowIndex(stage)
        if index >= 0 && (m.runFlow[index].Status == runFlowPending || m.runFlow[index].Status == runFlowActive) {
            m.runFlow[index].Status = runFlowSkipped
        }
    }
}

func (m *model) skipPendingRunFlowBefore(index int) {
    for i := 0; i < index && i < len(m.runFlow); i++ {
        if m.runFlow[i].Status == runFlowPending {
            m.runFlow[i].Status = runFlowSkipped
        }
    }
}

func (m *model) failRunFlow(detail string) {
    for i := range m.runFlow {
        if m.runFlow[i].Status == runFlowActive {
            m.runFlow[i].Status = runFlowError
            m.runFlow[i].Detail = detail
            return
        }
    }
}

func (m *model) runFlowIndex(stage string) int {
    for i, node := range m.runFlow {
        if node.Stage == stage {
            return i
        }
    }
    return -1
}

var (
    titleStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#F5F7FA"))
    subtleStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
    selectedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#111820")).Background(lipgloss.Color("#8AD7C1")).Bold(true)
    helpStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("247"))
    errorStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF6B6B")).Bold(true)
    successStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#8AD7C1")).Bold(true)
    accentStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("#E8C96A")).Bold(true)
    panelStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(lipgloss.Color("238")).Padding(1, 2)
    activePanel   = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(lipgloss.Color("#8AD7C1")).Padding(1, 2)
    headerStyle   = lipgloss.NewStyle().Background(lipgloss.Color("#25303B")).Foreground(lipgloss.Color("#F5F7FA")).Bold(true).Padding(0, 1)
    footerStyle   = lipgloss.NewStyle().Background(lipgloss.Color("#1F2730")).Foreground(lipgloss.Color("250")).Padding(0, 1)
    keyStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("#8AD7C1")).Bold(true)
    labelStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("#E8C96A")).Bold(true)
)
```

## FILE: internal/tui/views.go

```go
package tui

import (
    "fmt"
    "strings"

    "github.com/charmbracelet/lipgloss"
    "github.com/tik-choco/rssflow/internal/rssflow"
)

func (m *model) viewList() string {
    width := m.contentWidth()
    var sb strings.Builder
    sb.WriteString(sectionTitle("Workflows"))
    sb.WriteString("\n")
    sb.WriteString(subtleStyle.Render(fmt.Sprintf("%d configured workflow(s)", len(m.config.Workflows))))
    sb.WriteString("\n\n")
    for i, wf := range m.config.Workflows {
        resolved := rssflow.ResolveWorkflow(m.config, wf)
        profile := wf.LLM.Profile
        if profile == "" {
            profile = "inline"
        }
        line := fmt.Sprintf("  %-22s  feeds %-2d  src %-2d  %-12s  %s", truncate(wf.Label, 22), len(wf.RSS.URLs), rssflow.CountConfiguredSources(wf.Sources), truncate(profile, 12), truncate(resolved.LLM.Model, width-66))
        if i == m.index {
            sb.WriteString(selectedStyle.Width(width - 4).Render("> " + line))
        } else {
            sb.WriteString(subtleStyle.Width(width - 4).Render("  " + line))
        }
        sb.WriteString("\n")
    }

    if len(m.config.Workflows) > 0 {
        sb.WriteString("\n")
        sb.WriteString(m.workflowDetails(width - 4))
    }

    body := panelStyle.Width(width).Render(sb.String())
    help := keyBar([]keyHelp{
        {"a", "add"}, {"A", "devnews"}, {"enter", "edit"}, {"p", "profiles"}, {"L", "llm"}, {"S", "stream"}, {"t", "dry-run"}, {"r", "run"}, {"q", "quit"},
    })
    return m.shell("rssflow", "workflow editor", body, help)
}

func (m *model) viewEdit() string {
    width := m.contentWidth()
    sections := []string{
        m.fieldSection("Workflow", []int{fieldLabel}, width),
        m.fieldSection("RSS", []int{fieldURLs, fieldLimit, fieldDedupe, fieldMaxSeen}, width),
        m.fieldSection("LLM", []int{fieldLLMProfile, fieldModel}, width),
        m.fieldSection("Agent", []int{fieldAgent, fieldAgentRole, fieldAgentLanguage, fieldOutputFormat, fieldAgentInstructions}, width),
    }
    help := keyBar([]keyHelp{
        {"tab", "next"}, {"shift+tab", "prev"}, {"enter/←/→", "select"}, {"ctrl+s", "save"}, {"esc", "cancel"},
    })
    body := cropLines(strings.Join(sections, "\n"), m.editOffset, m.editVisibleLines())
    return m.shell("edit workflow", labels[m.focus], body, help)
}

func (m *model) viewModels() string {
    width := m.contentWidth()
    var sb strings.Builder
    sb.WriteString(sectionTitle("Model Picker"))
    sb.WriteString("\n")
    if len(m.models) > 0 {
        sb.WriteString(subtleStyle.Render(fmt.Sprintf("%d model(s) from API", len(m.models))))
        sb.WriteString("\n")
    }
    sb.WriteString("\n")
    if m.err != nil {
        sb.WriteString(errorStyle.Render("error: " + m.err.Error()))
        sb.WriteString("\n")
    }
    if len(m.models) == 0 && m.err == nil {
        sb.WriteString(helpStyle.Render("loading or no models found"))
        sb.WriteString("\n")
    }
    start := 0
    end := len(m.models)
    if end > 24 {
        if m.modelIndex >= 24 {
            start = m.modelIndex - 23
        }
        end = start + 24
        if end > len(m.models) {
            end = len(m.models)
        }
    }
    for i := start; i < end; i++ {
        line := "  " + truncate(m.models[i], width-8)
        if i == m.modelIndex {
            sb.WriteString(selectedStyle.Width(width - 4).Render("> " + line))
        } else {
            sb.WriteString("  ")
            sb.WriteString(subtleStyle.Render(line))
        }
        sb.WriteString("\n")
    }
    sb.WriteString("\n")
    if len(m.models) > 24 {
        sb.WriteString(subtleStyle.Render(fmt.Sprintf("showing %d-%d of %d", start+1, end, len(m.models))))
    }

    body := panelStyle.Width(width).Render(sb.String())
    help := keyBar([]keyHelp{{"up/down", "move"}, {"enter", "select"}, {"esc", "back"}})
    return m.shell("models", "select an API model", body, help)
}

func (m *model) viewProfiles() string {
    width := m.contentWidth()
    var sb strings.Builder
    sb.WriteString(sectionTitle("LLM Profiles"))
    sb.WriteString("\n")
    sb.WriteString(subtleStyle.Render(fmt.Sprintf("%d reusable profile(s)", len(m.config.LLMProfiles))))
    sb.WriteString("\n\n")
    for i, profile := range m.config.LLMProfiles {
        line := fmt.Sprintf("  %-18s  %-28s  %s", truncate(profile.Label, 18), truncate(profile.BaseURL, 28), truncate(profile.Model, width-58))
        if i == m.profileIndex {
            sb.WriteString(selectedStyle.Width(width - 4).Render("> " + line))
        } else {
            sb.WriteString(subtleStyle.Width(width - 4).Render("  " + line))
        }
        sb.WriteString("\n")
    }
    body := panelStyle.Width(width).Render(sb.String())
    help := keyBar([]keyHelp{{"a", "add"}, {"enter/e", "edit"}, {"d", "delete"}, {"esc", "back"}})
    if m.profileReturn == modeEdit {
        help = keyBar([]keyHelp{{"up/down", "move"}, {"enter", "select"}, {"a", "add"}, {"e", "edit"}, {"esc", "back"}})
    }
    return m.shell("llm profiles", "shared API settings", body, help)
}

func (m *model) viewProfileEdit() string {
    width := m.contentWidth()
    var sb strings.Builder
    sb.WriteString(sectionTitle("Edit LLM Profile"))
    sb.WriteString("\n")
    for i, input := range m.profileFields {
        prefix := "  "
        if i == m.profileFocus {
            prefix = "> "
        }
        label := profileLabels[i]
        if i == profileFieldModel {
            label += "  " + subtleStyle.Render("(enter opens model picker)")
        }
        sb.WriteString(prefix)
        if i == m.profileFocus {
            sb.WriteString(labelStyle.Render(label))
        } else {
            sb.WriteString(subtleStyle.Render(label))
        }
        sb.WriteString("\n  ")
        sb.WriteString(input.View())
        sb.WriteString("\n")
    }
    body := panelStyle.Width(width).Render(sb.String())
    help := keyBar([]keyHelp{{"tab", "next"}, {"shift+tab", "prev"}, {"enter", "choose model"}, {"ctrl+s", "save"}, {"esc", "cancel"}})
    return m.shell("edit llm profile", profileLabels[m.profileFocus], body, help)
}

func (m *model) viewTest() string {
    width := m.contentWidth()
    title := "Run Workflow"
    subtitle := "fetch, summarize, and save state"
    running := "running workflow..."
    if m.resultLLMTest {
        title = "LLM Test"
        subtitle = "quick model response check"
        running = "checking LLM..."
    }
    if m.resultStreamTest {
        title = "LLM Stream Test"
        subtitle = "checks chunk delivery"
        running = "checking streaming..."
    }
    if m.resultDryRun {
        title = "Dry Run"
        subtitle = "fetch and dedupe without OpenAI"
        running = "running dry-run..."
    }
    if m.resultForce {
        title += " (Force)"
        subtitle += ", ignoring dedupe"
    }
    var sb strings.Builder
    sb.WriteString(sectionTitle(title))
    sb.WriteString("\n\n")
    if !m.resultLLMTest {
        sb.WriteString(m.runWorkflowBody(width-8, running))
    } else if m.resultOutput == "" {
        sb.WriteString(helpStyle.Render(running))
        sb.WriteString("\n")
    } else {
        sb.WriteString(cropLines(wrapText(m.resultOutput, width-8), m.resultOffset, m.resultVisibleLines()))
        if !m.resultDone {
            sb.WriteString("\n")
            sb.WriteString(helpStyle.Render("streaming..."))
        }
    }

    body := panelStyle.Width(width).Render(sb.String())
    help := keyBar([]keyHelp{{"arrows", "select"}, {"enter", "details"}, {"pgup/pgdown", "scroll"}, {"c/y", "copy manuscript"}, {"esc", "back"}})
    return m.shell(strings.ToLower(title), subtitle, body, help)
}

func (m *model) runWorkflowBody(width int, running string) string {
    if m.runDetailOpen && width >= 96 {
        leftWidth := width * 2 / 3
        rightWidth := width - leftWidth - 4
        if rightWidth < 44 {
            rightWidth = 44
            leftWidth = width - rightWidth - 4
        }
        left := m.runFlowPanel(leftWidth)
        right := m.runDetailPanel(rightWidth, running)
        return lipgloss.JoinHorizontal(lipgloss.Top, left, strings.Repeat(" ", 4), right)
    }

    var sb strings.Builder
    sb.WriteString(m.runFlowPanel(width))
    if m.runDetailOpen {
        sb.WriteString("\n\n")
        sb.WriteString(m.runDetailPanel(width, running))
    } else if strings.TrimSpace(m.resultDraft) != "" {
        sb.WriteString("\n\n")
        sb.WriteString(m.runOutputPanel(width))
    }
    return sb.String()
}

func (m *model) runFlowPanel(width int) string {
    graph := m.runFlowGraph(width - 4)
    if graph == "" {
        graph = helpStyle.Render("waiting for workflow progress")
    }
    graph = cropLines(graph, m.runFlowOffset, m.runFlowVisibleLines())
    title := sectionTitle("Flow Grid")
    if m.runDetailOpen {
        title += subtleStyle.Render("  enter to close details")
    } else {
        title += keyStyle.Render("  arrows select")
    }
    style := activePanel
    return style.Width(width).Render(title + "\n" + graph)
}

func (m *model) runDetailPanel(width int, running string) string {
    text := m.runDetailText(width - 4)
    if text == "" {
        text = helpStyle.Render(running)
    }
    text = cropLines(text, m.runDetailOffset, m.runDetailVisibleLines())
    return activePanel.Width(width).Render(text)
}

func (m *model) runOutputPanel(width int) string {
    var sb strings.Builder
    sb.WriteString(sectionTitle(m.resultOutputSectionTitle()))
    sb.WriteString("\n")
    output := strings.TrimSpace(m.resultDraft)
    if output == "" {
        output = strings.TrimSpace(m.resultOutput)
    }
    if output == "" {
        sb.WriteString(helpStyle.Render("output is not ready yet"))
    } else {
        lines := 10
        if m.height < 28 {
            lines = 6
        }
        sb.WriteString(cropLines(wrapText(output, width-4), m.resultOffset, lines))
    }
    return panelStyle.Width(width).Render(sb.String())
}

func (m *model) runDetailText(width int) string {
    if len(m.runFlow) == 0 || m.selectedRunFlow < 0 || m.selectedRunFlow >= len(m.runFlow) {
        return ""
    }
    node := m.runFlow[m.selectedRunFlow]
    var sb strings.Builder
    sb.WriteString(sectionTitle(node.Label))
    sb.WriteString("\n")
    sb.WriteString(kv("Stage", node.Stage))
    sb.WriteString(kv("Status", runFlowStatusLabel(node.Status)))
    if node.Kind != "" {
        sb.WriteString(kv("Type", node.Kind))
    }
    if node.Description != "" {
        sb.WriteString("\n")
        sb.WriteString(labelStyle.Render("What"))
        sb.WriteString("\n")
        sb.WriteString(wrapText(node.Description, width))
        sb.WriteString("\n")
    }
    if node.Detail != "" {
        sb.WriteString("\n\n")
        sb.WriteString(labelStyle.Render("Current detail"))
        sb.WriteString("\n")
        sb.WriteString(wrapText(node.Detail, width))
        sb.WriteString("\n")
    }
    if ranking := m.runNodeRankingBoard(node.Stage, width); ranking != "" {
        sb.WriteString("\n\n")
        sb.WriteString(ranking)
    }
    logs := m.runStageLogs[node.Stage]
    if len(logs) > 0 {
        sb.WriteString("\n\n")
        sb.WriteString(labelStyle.Render("Log"))
        sb.WriteString("\n")
        for _, line := range logs {
            sb.WriteString("  ")
            sb.WriteString(wrapText(line, width-2))
            sb.WriteString("\n")
        }
    }
    if runStageShowsOutput(node.Stage) && strings.TrimSpace(m.resultDraft) != "" {
        sb.WriteString("\n")
        sb.WriteString(labelStyle.Render(m.resultOutputSectionTitle()))
        sb.WriteString("\n")
        sb.WriteString(wrapText(strings.TrimSpace(m.resultDraft), width))
        sb.WriteString("\n")
    }
    if m.err != nil {
        sb.WriteString("\n")
        sb.WriteString(errorStyle.Render("error: " + m.err.Error()))
    }
    return strings.TrimRight(sb.String(), "\n")
}

func runStageShowsOutput(stage string) bool {
    switch stage {
    case "render", "generate", "done":
        return true
    default:
        return false
    }
}

func (m *model) runNodeRankingBoard(stage string, width int) string {
    switch stage {
    case "score", "sort", "arc", "limit":
        return m.runRankingBoard(width)
    default:
        return ""
    }
}

func (m *model) runRankingBoard(width int) string {
    if len(m.rankingTopics) == 0 {
        return ""
    }
    var sb strings.Builder
    sb.WriteString(sectionTitle("Ranking"))
    if label := rankingStageLabel(m.rankingStage); label != "" {
        sb.WriteString(subtleStyle.Render("  " + label))
    }
    sb.WriteString("\n")
    barWidth := width - 34
    if barWidth < 8 {
        barWidth = 8
    }
    if barWidth > 22 {
        barWidth = 22
    }
    max := len(m.rankingTopics)
    if max > 8 {
        max = 8
    }
    for i := 0; i < max; i++ {
        topic := m.rankingTopics[i]
        style := rankingToneStyle(topic.Tone)
        score := topic.Score
        if score < 0 {
            score = 0
        }
        if score > 100 {
            score = 100
        }
        fill := score * barWidth / 100
        if m.rankingStage == "score" && i == m.runFlowPhase%max && fill < barWidth {
            fill++
        }
        bar := strings.Repeat("█", fill) + subtleStyle.Render(strings.Repeat("░", barWidth-fill))
        titleWidth := width - barWidth - 12
        if titleWidth < 12 {
            titleWidth = 12
        }
        line := fmt.Sprintf("%2d %3d ", topic.Rank, score)
        sb.WriteString(style.Render(line))
        sb.WriteString(style.Render(bar))
        sb.WriteString(" ")
        sb.WriteString(truncate(topic.Title, titleWidth))
        if topic.Tone != "" {
            sb.WriteString(subtleStyle.Render(" " + rankingToneBadge(topic.Tone)))
        }
        sb.WriteString("\n")
    }
    if len(m.rankingTopics) > max {
        sb.WriteString(subtleStyle.Render(fmt.Sprintf("+ %d more topic(s)", len(m.rankingTopics)-max)))
        sb.WriteString("\n")
    }
    return strings.TrimRight(sb.String(), "\n")
}

func rankingStageLabel(stage string) string {
    switch stage {
    case "score":
        return "scoring"
    case "sort":
        return "sorted by score"
    case "arc":
        return "story arc"
    case "limit":
        return "final input"
    default:
        return ""
    }
}

func rankingToneStyle(tone string) lipgloss.Style {
    switch tone {
    case "hard_negative":
        return errorStyle
    case "constructive":
        return keyStyle
    case "bright":
        return successStyle
    default:
        return helpStyle
    }
}

func rankingToneBadge(tone string) string {
    switch tone {
    case "hard_negative":
        return "hard"
    case "constructive":
        return "construct"
    case "bright":
        return "bright"
    default:
        return tone
    }
}

func (m *model) runFlowGraph(width int) string {
    if len(m.runFlow) == 0 {
        return ""
    }
    return m.runFlowGrid(width)
}

func (m *model) runFlowGrid(width int) string {
    cols := 1
    switch {
    case width >= 92:
        cols = 4
    case width >= 72:
        cols = 3
    case width >= 46:
        cols = 2
    }
    gap := 3
    cellWidth := (width - gap*(cols-1)) / cols
    if cellWidth < 20 {
        cols = 1
        cellWidth = width
    }

    var sb strings.Builder
    for rowStart := 0; rowStart < len(m.runFlow); rowStart += cols {
        rowEnd := rowStart + cols
        if rowEnd > len(m.runFlow) {
            rowEnd = len(m.runFlow)
        }
        cards := make([][]string, 0, rowEnd-rowStart)
        for i := rowStart; i < rowEnd; i++ {
            cards = append(cards, strings.Split(m.runFlowCard(i, m.runFlow[i], cellWidth, i == m.selectedRunFlow), "\n"))
        }
        for line := 0; line < 5; line++ {
            for col, card := range cards {
                if col > 0 {
                    leftIndex := rowStart + col - 1
                    rightIndex := rowStart + col
                    sb.WriteString(m.gridHorizontalConnector(m.runFlow[leftIndex], m.runFlow[rightIndex], gap, line))
                }
                if line < len(card) {
                    sb.WriteString(card[line])
                } else {
                    sb.WriteString(strings.Repeat(" ", cellWidth))
                }
            }
            sb.WriteString("\n")
        }
        if rowEnd < len(m.runFlow) {
            sb.WriteString(m.gridRowConnector(width, cols, cellWidth, gap, rowStart/cols))
            sb.WriteString("\n")
        }
    }
    return strings.TrimRight(sb.String(), "\n")
}

func (m *model) runFlowCard(index int, node runFlowNode, width int, selected bool) string {
    style := subtleStyle
    marker := "○"
    if node.Kind == "condition" {
        marker = "◇"
    }
    switch node.Status {
    case runFlowDone:
        style = successStyle
        if node.Kind == "condition" {
            marker = "◆"
        } else {
            marker = "●"
        }
    case runFlowActive:
        style = keyStyle
        if node.Kind == "condition" {
            marker = "◈"
        } else {
            marker = "◉"
        }
    case runFlowSkipped:
        style = subtleStyle
        marker = "○"
    case runFlowError:
        style = errorStyle
        marker = "!"
    }
    if selected {
        style = selectedStyle
    }

    labelWidth := width - 2
    if labelWidth < 12 {
        labelWidth = 12
    }
    topLeft, topRight, bottomLeft, bottomRight, horizontal := "╭", "╮", "╰", "╯", "─"
    if selected {
        topLeft, topRight, bottomLeft, bottomRight, horizontal = "╔", "╗", "╚", "╝", "═"
    }
    top := topLeft + strings.Repeat(horizontal, width-2) + topRight
    bottom := bottomLeft + strings.Repeat(horizontal, width-2) + bottomRight
    step := fmt.Sprintf("%02d", index+1)
    title := padRightRunes(marker+" "+step+" "+truncate(node.Label, labelWidth-5), labelWidth)
    desc := padRightRunes(truncate(node.Description, labelWidth), labelWidth)
    detail := node.Detail
    if detail == "" {
        detail = runFlowStatusLabel(node.Status)
    }
    detail = padRightRunes(truncate(detail, labelWidth), labelWidth)

    var sb strings.Builder
    sb.WriteString(style.Render(top))
    sb.WriteString("\n")
    sb.WriteString(style.Render("│" + title + "│"))
    sb.WriteString("\n")
    sb.WriteString(subtleStyle.Render("│" + desc + "│"))
    sb.WriteString("\n")
    sb.WriteString(style.Render("│" + detail + "│"))
    sb.WriteString("\n")
    sb.WriteString(style.Render(bottom))
    return sb.String()
}

func (m *model) gridRowConnector(width, cols, cellWidth, gap, row int) string {
    if cols == 1 {
        return subtleStyle.Render("  │")
    }
    marker := "│"
    style := subtleStyle
    if m.rowHasActiveConnector(row, cols) {
        frames := []string{"┃", "╽", "╿"}
        marker = frames[(m.runFlowPhase+row)%len(frames)]
        style = keyStyle
    }
    segments := make([]string, 0, cols)
    segments = append(segments, centerText(marker, cellWidth))
    for i := 1; i < cols; i++ {
        segments = append(segments, strings.Repeat(" ", cellWidth))
    }
    return style.Render(truncate(strings.Join(segments, strings.Repeat(" ", gap)), width))
}

func (m *model) gridHorizontalConnector(left, right runFlowNode, width, line int) string {
    if width <= 0 {
        return ""
    }
    if line != 2 {
        return strings.Repeat(" ", width)
    }
    text := "──▶"
    style := subtleStyle
    switch {
    case left.Status == runFlowError || right.Status == runFlowError:
        text = "─╳─"
        style = errorStyle
    case left.Status == runFlowDone && right.Status == runFlowActive:
        frames := []string{"━▶ ", "━━▶", " ━▶"}
        text = frames[m.runFlowPhase%len(frames)]
        style = keyStyle
    case left.Status == runFlowDone || left.Status == runFlowSkipped:
        text = "──▶"
        style = successStyle
    }
    return style.Render(centerText(text, width))
}

func (m *model) rowHasActiveConnector(row, cols int) bool {
    last := (row+1)*cols - 1
    next := last + 1
    if last < 0 || next >= len(m.runFlow) {
        return false
    }
    return m.runFlow[last].Status == runFlowDone && m.runFlow[next].Status == runFlowActive
}

func runFlowStatusLabel(status runFlowStatus) string {
    switch status {
    case runFlowDone:
        return "done"
    case runFlowActive:
        return "running"
    case runFlowSkipped:
        return "skipped"
    case runFlowError:
        return "error"
    default:
        return "waiting"
    }
}

func (m *model) runChatText(width int) string {
    var sb strings.Builder
    messages := compactChatMessages(m.resultMessages, 8)
    for _, msg := range messages {
        if msg.Text == "" {
            continue
        }
        prefix := "agent"
        style := subtleStyle
        switch msg.Role {
        case "you":
            prefix = "you"
            style = keyStyle
        case "summary":
            prefix = "summary"
            style = helpStyle
        }
        sb.WriteString(style.Render(prefix))
        sb.WriteString("\n")
        sb.WriteString(indentText(wrapText(msg.Text, width-4), "  "))
        sb.WriteString("\n\n")
    }
    if strings.TrimSpace(m.resultDraft) != "" {
        sb.WriteString(sectionTitle(m.resultOutputSectionTitle()))
        sb.WriteString("\n")
        draft := strings.TrimSpace(m.resultDraft)
        if !m.resultDone {
            draft += "\n\n" + helpStyle.Render("...")
        }
        sb.WriteString(wrapText(draft, width))
        sb.WriteString("\n")
    }
    return strings.TrimRight(sb.String(), "\n")
}

func (m *model) resultOutputSectionTitle() string {
    if len(m.config.Workflows) == 0 || m.index >= len(m.config.Workflows) {
        return "Output"
    }
    wf := rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
    switch rssflow.NormalizeOutputFormat(wf.Agent.OutputFormat) {
    case rssflow.OutputFormatNewsScript:
        return "News Script"
    case rssflow.OutputFormatArticle:
        return "Article"
    default:
        return "Podcast Script"
    }
}

func compactChatMessages(messages []runChatMessage, max int) []runChatMessage {
    if len(messages) <= max || max < 4 {
        return messages
    }
    head := max / 2
    tail := max - head - 1
    out := make([]runChatMessage, 0, max)
    out = append(out, messages[:head]...)
    out = append(out, runChatMessage{
        Role: "summary",
        Text: fmt.Sprintf("%d progress message(s) hidden to keep the run readable", len(messages)-head-tail),
    })
    out = append(out, messages[len(messages)-tail:]...)
    return out
}

func indentText(s, prefix string) string {
    if s == "" {
        return ""
    }
    lines := strings.Split(s, "\n")
    for i := range lines {
        if lines[i] != "" {
            lines[i] = prefix + lines[i]
        }
    }
    return strings.Join(lines, "\n")
}

func (m *model) workflowDetails(width int) string {
    wf := rssflow.ResolveWorkflow(m.config, m.config.Workflows[m.index])
    raw := m.config.Workflows[m.index]
    var sb strings.Builder
    sb.WriteString(sectionTitle("Selected"))
    sb.WriteString("\n")
    sb.WriteString(kv("Label", wf.Label))
    sb.WriteString(kv("Profile", profileLabel(raw.LLM.Profile)))
    sb.WriteString(kv("Model", wf.LLM.Model))
    sb.WriteString(kv("Base URL", wf.LLM.BaseURL))
    sb.WriteString(kv("Format", rssflow.OutputFormatLabel(wf.Agent.OutputFormat)))
    sb.WriteString(kv("RSS feeds", fmt.Sprintf("%d", len(wf.RSS.URLs))))
    sb.WriteString(kv("Sources", fmt.Sprintf("%d", rssflow.CountConfiguredSources(wf.Sources))))
    sb.WriteString(kv("Dedupe", boolBadge(wf.Dedupe.Enabled)))
    if len(wf.RSS.URLs) > 0 {
        sb.WriteString("\n")
        sb.WriteString(labelStyle.Render("Feeds"))
        sb.WriteString("\n")
        for i, url := range wf.RSS.URLs {
            if i == 3 {
                sb.WriteString(subtleStyle.Render(fmt.Sprintf("  + %d more\n", len(wf.RSS.URLs)-i)))
                break
            }
            sb.WriteString("  ")
            sb.WriteString(truncate(url, width-4))
            sb.WriteString("\n")
        }
    }
    if rssflow.CountConfiguredSources(wf.Sources) > 0 {
        sb.WriteString("\n")
        sb.WriteString(labelStyle.Render("Sources"))
        sb.WriteString("\n")
        for _, line := range sourcePreview(wf.Sources, 4) {
            sb.WriteString("  ")
            sb.WriteString(truncate(line, width-4))
            sb.WriteString("\n")
        }
    }
    return activePanel.Width(width).Render(sb.String())
}

func (m *model) fieldSection(title string, fields []int, width int) string {
    var sb strings.Builder
    sb.WriteString(sectionTitle(title))
    sb.WriteString("\n")
    for _, field := range fields {
        sb.WriteString(m.renderField(field))
    }
    style := panelStyle
    if containsField(fields, m.focus) {
        style = activePanel
    }
    return style.Width(width).Render(sb.String())
}

func (m *model) renderField(field int) string {
    focused := field == m.focus
    label := labels[field]
    if field == fieldModel {
        label += "  " + subtleStyle.Render("(enter opens model picker)")
    }
    if field == fieldLLMProfile {
        label += "  " + subtleStyle.Render("(enter opens profile picker)")
    }
    if field == fieldOutputFormat {
        label += "  " + subtleStyle.Render("(enter or left/right selects)")
    }
    prefix := "  "
    if focused {
        prefix = "> "
    }
    var sb strings.Builder
    sb.WriteString(prefix)
    if focused {
        sb.WriteString(labelStyle.Render(label))
    } else {
        sb.WriteString(subtleStyle.Render(label))
    }
    sb.WriteString("\n  ")
    if field == fieldOutputFormat {
        sb.WriteString(m.outputFormatSelector())
    } else {
        sb.WriteString(m.fields[field].View())
    }
    sb.WriteString("\n")
    return sb.String()
}

func (m *model) outputFormatSelector() string {
    current := rssflow.NormalizeOutputFormat(m.fields[fieldOutputFormat].Value())
    var parts []string
    for _, format := range rssflow.OutputFormats() {
        label := format
        if format == current {
            parts = append(parts, selectedStyle.Render("["+label+"]"))
        } else {
            parts = append(parts, subtleStyle.Render(" "+label+" "))
        }
    }
    return strings.Join(parts, "  ")
}

func (m *model) shell(title, subtitle, body, help string) string {
    width := m.contentWidth()
    header := headerStyle.Width(width).Render(titleStyle.Render(title) + subtleStyle.Render("  "+subtitle))
    status := m.statusLine(width)
    footer := footerStyle.Width(width).Render(help)
    return lipgloss.JoinVertical(lipgloss.Left, header, status, body, footer)
}

func (m *model) statusLine(width int) string {
    if m.err != nil {
        return errorStyle.Width(width).Render("error: " + truncate(m.err.Error(), width-8))
    }
    if m.info != "" {
        return successStyle.Width(width).Render(truncate(m.info, width))
    }
    if len(m.config.Workflows) == 0 {
        return subtleStyle.Width(width).Render("no workflows")
    }
    wf := m.config.Workflows[m.index]
    resolved := rssflow.ResolveWorkflow(m.config, wf)
    text := fmt.Sprintf("%s  |  %s  |  %s  |  %d feed(s)", wf.Label, profileLabel(wf.LLM.Profile), resolved.LLM.Model, len(wf.RSS.URLs))
    return subtleStyle.Width(width).Render(truncate(text, width))
}

type keyHelp struct {
    key  string
    desc string
}

func keyBar(items []keyHelp) string {
    parts := make([]string, 0, len(items))
    for _, item := range items {
        parts = append(parts, keyStyle.Render(item.key)+" "+item.desc)
    }
    return strings.Join(parts, "   ")
}

func sectionTitle(title string) string {
    return accentStyle.Render(strings.ToUpper(title))
}

func kv(key, value string) string {
    return fmt.Sprintf("  %-10s %s\n", key, value)
}

func boolBadge(value bool) string {
    if value {
        return successStyle.Render("enabled")
    }
    return subtleStyle.Render("disabled")
}

func profileLabel(label string) string {
    if label == "" {
        return "inline"
    }
    return label
}

func sourcePreview(s rssflow.SourcesConfig, limit int) []string {
    lines := []string{}
    appendValues := func(prefix string, values []string) {
        for _, value := range values {
            lines = append(lines, prefix+": "+value)
            if len(lines) == limit {
                return
            }
        }
    }
    appendValues("github release", s.GitHub.Releases)
    if len(lines) < limit {
        appendValues("github tag", s.GitHub.Tags)
    }
    if len(lines) < limit && s.GitHub.Advisories.Enabled {
        lines = append(lines, "github advisories")
    }
    if len(lines) < limit {
        appendValues("npm", s.Packages.NPM)
    }
    if len(lines) < limit {
        appendValues("pypi", s.Packages.PyPI)
    }
    if len(lines) < limit {
        appendValues("crates", s.Packages.Crates)
    }
    if len(lines) < limit {
        appendValues("nvd", s.Security.NVD.Keywords)
    }
    total := rssflow.CountConfiguredSources(s)
    if total > len(lines) {
        lines = append(lines, fmt.Sprintf("+ %d more", total-len(lines)))
    }
    return lines
}

func cropLines(s string, offset, height int) string {
    lines := strings.Split(s, "\n")
    if height <= 0 || len(lines) <= height {
        return s
    }
    if offset < 0 {
        offset = 0
    }
    if offset > len(lines)-height {
        offset = len(lines) - height
    }
    out := lines[offset : offset+height]
    if offset > 0 {
        out[0] = subtleStyle.Render("...") + out[0]
    }
    if offset+height < len(lines) {
        out[len(out)-1] = out[len(out)-1] + subtleStyle.Render(" ...")
    }
    return strings.Join(out, "\n")
}

func wrapText(s string, width int) string {
    if width <= 8 {
        return s
    }
    var out []string
    for _, line := range strings.Split(s, "\n") {
        runes := []rune(line)
        for len(runes) > width {
            out = append(out, string(runes[:width]))
            runes = runes[width:]
        }
        out = append(out, string(runes))
    }
    return strings.Join(out, "\n")
}

func containsField(fields []int, target int) bool {
    for _, field := range fields {
        if field == target {
            return true
        }
    }
    return false
}

func truncate(s string, width int) string {
    if width <= 0 {
        return ""
    }
    runes := []rune(s)
    if len(runes) <= width {
        return s
    }
    if width <= 1 {
        return string(runes[:width])
    }
    return string(runes[:width-1]) + "~"
}

func padRightRunes(s string, width int) string {
    padding := width - lipgloss.Width(s)
    if padding <= 0 {
        return s
    }
    return s + strings.Repeat(" ", padding)
}

func centerText(s string, width int) string {
    used := lipgloss.Width(s)
    if used >= width {
        return truncate(s, width)
    }
    left := (width - used) / 2
    right := width - used - left
    return strings.Repeat(" ", left) + s + strings.Repeat(" ", right)
}
```

## FILE: internal/tui/views_test.go

```go
package tui

import (
    "bytes"
    "strings"
    "testing"
    "unicode/utf8"

    "github.com/tik-choco/rssflow/internal/rssflow"
)

func TestCompactChatMessagesKeepsHeadTail(t *testing.T) {
    messages := []runChatMessage{
        {Role: "agent", Text: "one"},
        {Role: "agent", Text: "two"},
        {Role: "agent", Text: "three"},
        {Role: "agent", Text: "four"},
        {Role: "agent", Text: "five"},
        {Role: "agent", Text: "six"},
    }
    got := compactChatMessages(messages, 4)
    if len(got) != 4 {
        t.Fatalf("len = %d, want 4", len(got))
    }
    if got[0].Text != "one" || got[1].Text != "two" {
        t.Fatalf("head not preserved: %#v", got)
    }
    if got[2].Role != "summary" {
        t.Fatalf("summary role = %q", got[2].Role)
    }
    if got[3].Text != "six" {
        t.Fatalf("tail not preserved: %#v", got)
    }
}

func TestWrapTextDoesNotSplitJapaneseRunes(t *testing.T) {
    got := wrapText("デベロッパーニュース。今日の主なトピックです。", 12)
    if strings.ContainsRune(got, utf8.RuneError) {
        t.Fatalf("wrap produced replacement rune: %q", got)
    }
    for _, line := range strings.Split(got, "\n") {
        if len([]rune(line)) > 12 {
            t.Fatalf("line rune len = %d, want <= 12: %q", len([]rune(line)), line)
        }
    }
}

func TestTruncateDoesNotSplitJapaneseRunes(t *testing.T) {
    got := truncate("デベロッパーニュース", 7)
    if strings.ContainsRune(got, utf8.RuneError) {
        t.Fatalf("truncate produced replacement rune: %q", got)
    }
    if got != "デベロッパー~" {
        t.Fatalf("truncate = %q", got)
    }
}

func TestOutputFormatSelectorShowsChoices(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    cfg.Workflows[0].Agent.OutputFormat = rssflow.OutputFormatArticle
    m := newModel("", cfg)

    got := m.outputFormatSelector()
    for _, want := range []string{"news-script", "podcast", "[article]"} {
        if !strings.Contains(got, want) {
            t.Fatalf("selector missing %q:\n%s", want, got)
        }
    }
}

func TestRunFlowAdvancesAndRendersGraph(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.startResult(false, false)
    m.advanceRunFlow("collect", "collecting items")
    m.advanceRunFlow("filter", "checking seen state")

    got := m.runFlowGraph(120)
    for _, want := range []string{"● 01 Start", "● 02 Collect feeds", "● 03 Load state", "◉ 04 Filter items", "checking seen state", "◇ 05 New items?", "◇ 06 Dry run?"} {
        if !strings.Contains(got, want) {
            t.Fatalf("graph missing %q:\n%s", want, got)
        }
    }
}

func TestRunFlowPanelCropsGridWithScrollOffset(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.height = 24
    m.startResult(false, false)
    m.runFlowOffset = 6

    got := m.runFlowPanel(64)
    if strings.Contains(got, "● 01 Start") {
        t.Fatalf("expected scrolled panel to crop first card:\n%s", got)
    }
    if !strings.Contains(got, "FLOW GRID") {
        t.Fatalf("panel missing title:\n%s", got)
    }
}

func TestRunFlowGridShowsHorizontalConnectors(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.startResult(false, false)
    m.advanceRunFlow("collect", "collecting items")

    got := m.runFlowGraph(120)
    if !strings.Contains(got, "──▶") && !strings.Contains(got, "━▶") && !strings.Contains(got, "━━▶") {
        t.Fatalf("grid missing horizontal connector:\n%s", got)
    }
}

func TestRunFlowSkipsAlternativeBranches(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.startResult(false, false)
    m.advanceRunFlow("client", "preparing LLM")

    render := m.runFlowIndex("render")
    if render < 0 || m.runFlow[render].Status != runFlowSkipped {
        t.Fatalf("render status = %#v, want skipped", m.runFlow[render])
    }

    m.advanceRunFlow("save-check", "condition: dedupe disabled; skip seen state save")
    m.advanceRunFlow("done", "ready")
    save := m.runFlowIndex("save")
    if save < 0 || m.runFlow[save].Status != runFlowSkipped {
        t.Fatalf("save status = %#v, want skipped", m.runFlow[save])
    }
}

func TestRunRankingBoardShowsScoresAndTone(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.rankingStage = "sort"
    m.rankingTopics = []runRankTopic{
        {Rank: 1, Title: "critical package advisory", Score: 95, Tone: "hard_negative"},
        {Rank: 2, Title: "maintainer publishes migration guide", Score: 72, Tone: "constructive"},
    }

    got := m.runRankingBoard(80)
    for _, want := range []string{"RANKING", "sorted by score", "95", "critical package advisory", "hard", "72", "construct"} {
        if !strings.Contains(got, want) {
            t.Fatalf("ranking board missing %q:\n%s", want, got)
        }
    }
}

func TestCopyableResultTextPrefersManuscript(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.resultOutput = "log text"
    m.resultDraft = "final manuscript"

    if got := m.copyableResultText(); got != "final manuscript" {
        t.Fatalf("copyable text = %q, want manuscript", got)
    }
}

func TestWriteOSC52WritesTerminalSequence(t *testing.T) {
    var buf bytes.Buffer
    writeOSC52("final manuscript", &buf)
    if buf.Len() == 0 {
        t.Fatal("OSC52 writer produced no output")
    }
    if !strings.Contains(buf.String(), "\x1b]52;") {
        t.Fatalf("OSC52 output missing clipboard sequence: %q", buf.String())
    }
}

func TestRunDetailTextShowsSelectedNodeLog(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.startResult(false, false)
    m.advanceRunFlow("score", "received 2 topic score(s)")
    m.appendRunStageLog("score", "asking model to score topics")
    m.selectedRunFlow = m.runFlowIndex("score")

    got := m.runDetailText(80)
    for _, want := range []string{"SCORE TOPICS", "Stage", "score", "received 2 topic score(s)", "asking model to score topics"} {
        if !strings.Contains(got, want) {
            t.Fatalf("detail missing %q:\n%s", want, got)
        }
    }
}

func TestRunWorkflowBodyShowsOutputWhenDetailsClosed(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.startResult(false, false)
    m.resultDraft = "完成した原稿です。"
    m.resultOutput = m.resultDraft

    got := m.runWorkflowBody(100, "running")
    for _, want := range []string{"FLOW GRID", "PODCAST SCRIPT", "完成した原稿です。"} {
        if !strings.Contains(got, want) {
            t.Fatalf("body missing %q:\n%s", want, got)
        }
    }
}

func TestDoneDetailShowsOutput(t *testing.T) {
    cfg := rssflow.DefaultConfig()
    m := newModel("", cfg)
    m.startResult(false, false)
    m.resultDraft = "最終出力"
    m.selectedRunFlow = m.runFlowIndex("done")

    got := m.runDetailText(80)
    if !strings.Contains(got, "最終出力") {
        t.Fatalf("done detail missing output:\n%s", got)
    }
}
```
