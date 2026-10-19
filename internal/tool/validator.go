package tool

import (
	"encoding/json"
	"fmt"
)

// SchemaDefinition 用于解析工具参数的 JSON Schema 基础结构
type SchemaDefinition struct {
	Type       string                        `json:"type"`
	Required   []string                      `json:"required"`
	Properties map[string]PropertyDefinition `json:"properties"`
}

type PropertyDefinition struct {
	Type        string `json:"type"`
	Description string `json:"description"`
}

// ValidateArguments 根据 Schema 校验传入的工具调用参数
func ValidateArguments(schemaRaw, argsRaw json.RawMessage) error {
	if len(argsRaw) == 0 {
		argsRaw = json.RawMessage("{}")
	}

	var parsedArgs map[string]interface{}
	if err := json.Unmarshal(argsRaw, &parsedArgs); err != nil {
		return fmt.Errorf("malformed JSON arguments: %w", err)
	}

	if len(schemaRaw) == 0 {
		return nil
	}

	// Schema 由代码内静态定义，解析失败属程序缺陷。校验层必须 fail-closed：
	// 宁可拒绝执行，也不能让未经校验的参数进入工具本体。
	var schema SchemaDefinition
	if err := json.Unmarshal(schemaRaw, &schema); err != nil {
		return fmt.Errorf("invalid tool schema: %w", err)
	}

	// 校验必填字段
	for _, reqKey := range schema.Required {
		val, exists := parsedArgs[reqKey]
		if !exists || val == nil {
			return fmt.Errorf("missing required parameter %q", reqKey)
		}
		if strVal, ok := val.(string); ok && strVal == "" {
			return fmt.Errorf("required parameter %q cannot be empty", reqKey)
		}
	}

	// 校验字段基本类型
	for propName, propDef := range schema.Properties {
		val, exists := parsedArgs[propName]
		if !exists || val == nil {
			continue
		}

		switch propDef.Type {
		case "string":
			if _, ok := val.(string); !ok {
				return fmt.Errorf("parameter %q must be a string", propName)
			}
		case "integer", "number":
			if _, ok := val.(float64); !ok {
				return fmt.Errorf("parameter %q must be a number", propName)
			}
		case "boolean":
			if _, ok := val.(bool); !ok {
				return fmt.Errorf("parameter %q must be a boolean", propName)
			}
		case "array":
			if _, ok := val.([]interface{}); !ok {
				return fmt.Errorf("parameter %q must be an array", propName)
			}
		case "object":
			if _, ok := val.(map[string]interface{}); !ok {
				return fmt.Errorf("parameter %q must be an object", propName)
			}
		}
	}

	return nil
}
