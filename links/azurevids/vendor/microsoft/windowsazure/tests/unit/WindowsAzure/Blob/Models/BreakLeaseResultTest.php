<?php

/**
 * LICENSE: Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * 
 * PHP version 5
 *
 * @category  Microsoft
 * @package   Tests\Unit\WindowsAzure\Blob\Models
 * @author    Azure PHP SDK <azurephpsdk@microsoft.com>
 * @copyright 2012 Microsoft Corporation
 * @license   http://www.apache.org/licenses/LICENSE-2.0  Apache License 2.0
 * @link      https://github.com/windowsazure/azure-sdk-for-php
 */
namespace Tests\Unit\WindowsAzure\Blob\Models;
use WindowsAzure\Blob\Models\BreakLeaseResult;

/**
 * Unit tests for class BreakLeaseResult
 *
 * @category  Microsoft
 * @package   Tests\Unit\WindowsAzure\Blob\Models
 * @author    Azure PHP SDK <azurephpsdk@microsoft.com>
 * @copyright 2012 Microsoft Corporation
 * @license   http://www.apache.org/licenses/LICENSE-2.0  Apache License 2.0
 * @version   Release: 0.4.1_2015-03
 * @link      https://github.com/windowsazure/azure-sdk-for-php
 */
class BreakLeaseResultTest extends \PHPUnit_Framework_TestCase
{
    /**
     * @covers WindowsAzure\Blob\Models\BreakLeaseResult::create
     */
    public function testCreate()
    {
        // Setup
        $expected = '10';
        $headers = array('x-ms-lease-time' => $expected);
        
        // Test
        $result = BreakLeaseResult::create($headers);
        
        // Assert
        $this->assertEquals($expected, $result->getLeaseTime());
    }
    
    /**
     * @covers WindowsAzure\Blob\Models\BreakLeaseResult::setLeaseTime
     * @covers WindowsAzure\Blob\Models\BreakLeaseResult::getLeaseTime
     */
    public function testSetLeaseTime()
    {
        // Setup
        $expected = '0x8CAFB82EFF70C46';
        $result = new BreakLeaseResult();
        $result->setLeaseTime($expected);
        
        // Test
        $result->setLeaseTime($expected);
        
        // Assert
        $this->assertEquals($expected, $result->getLeaseTime());
    }
}